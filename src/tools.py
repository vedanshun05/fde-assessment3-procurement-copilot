"""Five read-only, request-scoped tools with a canonical evidence ledger."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import time
from typing import Callable

from pydantic import BaseModel, ConfigDict

from src.contracts import EvidenceItem, PurchaseRequest, RunTelemetry
from src.policy import evaluate_policy
from src.vendor_client import get_vendor_risk

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
POLICY_SHA256 = "f7eeea41d757308bc914a5e17f05064c4947e1cceaf2a70e3377b3a9c7cc8f32"
TOOL_DESCRIPTIONS = {
    "requester_budget": "Retrieve the requesting employee, department, manager, and available software budget.",
    "software_catalog": "Search approved products by product, vendor, category, use case, and department scope. Seat utilization is unknown.",
    "vendor_registry": "Retrieve internal vendor onboarding, security and legal status plus previous purchases.",
    "vendor_risk": "Call the external HTTP vendor/security risk endpoint; errors remain explicit evidence.",
    "policy_check": "Apply deterministic procurement policy 2026.09; collects missing evidence prerequisites and returns required approvals, missing info, risk flags.",
}
BASE_TOOLS = tuple(name for name in TOOL_DESCRIPTIONS if name != "policy_check")


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    vendor_name: str
    risk_level: str
    security_review_status: str
    last_review_date: str | None
    processes_personal_data: bool
    stores_data_outside_region: bool
    notes: str = ""


def csv_rows(name, data_dir):
    with (data_dir / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class ToolSet:
    def __init__(self, request: PurchaseRequest, telemetry: RunTelemetry, *, data_dir=DATA_DIR, risk_fetcher: Callable | None = None):
        self.request = request.model_dump()
        self.telemetry = telemetry
        self.data_dir = Path(data_dir)
        self.risk_fetcher = risk_fetcher or get_vendor_risk
        self.results: dict = {}
        self.evidence: list[EvidenceItem] = []

    def fact(self, source, finding, reference):
        item = EvidenceItem(evidence_id=f"E{len(self.evidence)+1:03d}", source=source, finding=finding, reference=reference)
        self.evidence.append(item)
        return item.evidence_id

    @property
    def schemas(self):
        return [{"type": "function", "name": name, "description": description,
                 "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                 "strict": True} for name, description in TOOL_DESCRIPTIONS.items()]

    def call(self, name: str, arguments: dict | None = None):
        if name not in TOOL_DESCRIPTIONS or arguments not in (None, {}):
            raise ValueError("Unknown tool or invalid request-scoped tool arguments")
        if name in self.results:
            return self.results[name]
        if name == "policy_check":
            for dependency in BASE_TOOLS:
                self.call(dependency)
        start = time.perf_counter()
        self.telemetry.tool_calls = (self.telemetry.tool_calls or 0) + 1
        self.telemetry.tool_names.append(name)
        before = len(self.evidence)
        try:
            result = getattr(self, name)()
        except Exception as exc:
            # Never expose credentials, URLs with secrets, or unrestricted exception text.
            result = {"status": "error", "error_type": type(exc).__name__}
            self.fact(name, f"Evidence unavailable: {name} failed ({type(exc).__name__}); favorable status was not assumed.", name)
        result["evidence_ids"] = [e.evidence_id for e in self.evidence[before:]]
        self.results[name] = result
        self.telemetry.tool_trace.append({"name": name, "status": result.get("status", "ok"),
                                          "latency_ms": round((time.perf_counter()-start)*1000, 3),
                                          "evidence_ids": result["evidence_ids"], "result": result,
                                          "evidence": [e.model_dump() for e in self.evidence[before:]]})
        return result

    def requester_budget(self):
        employee = next((x for x in csv_rows("employees.csv", self.data_dir) if x["employee_id"] == self.request["requester_id"]), None)
        budget = next((x for x in csv_rows("department_budgets.csv", self.data_dir) if employee and x["department"] == employee["department"]), None)
        manager = next((x for x in csv_rows("employees.csv", self.data_dir) if employee and x["employee_id"] == employee["manager_id"]), None)
        if employee:
            self.fact("requester_budget", f"Requester {employee['name']} belongs to {employee['department']}; manager: {manager['name'] if manager else 'not recorded'}.", f"employees.csv:{employee['employee_id']}")
        else:
            self.fact("requester_budget", "Requester identity and department could not be verified.", f"employees.csv:{self.request['requester_id'] or 'missing'}")
        if budget:
            self.fact("requester_budget", f"{budget['department']} has ${float(budget['available_usd']):,.2f} available software budget; requested annual amount: {self.request['annual_cost_usd'] if self.request['annual_cost_usd'] is not None else 'unknown'} USD.", f"department_budgets.csv:{budget['department']}")
        return {"status": "ok", "employee": employee, "manager": manager, "budget": budget}

    def software_catalog(self):
        employee = next((x for x in csv_rows("employees.csv", self.data_dir) if x["employee_id"] == self.request["requester_id"]), None)
        department = employee["department"] if employee else ""
        req = self.request
        text = (req["business_justification"] + " " + req["product_name"]).lower()
        use_cases = {"Project Management": ("task tracker", "project management", "task management"),
                     "Knowledge Management": ("knowledge base", "documentation"), "Observability": ("monitoring", "incident analytics"),
                     "Customer Support": ("support replies", "support ticket"), "E-signature": ("signing identities", "electronic signatures")}
        matches = []
        for row in csv_rows("software_catalog.csv", self.data_dir):
            reasons = []
            if row["product_name"].casefold() == req["product_name"].casefold(): reasons.append("same_product")
            if req["vendor_name"] and row["vendor_name"].casefold() == req["vendor_name"].casefold(): reasons.append("same_vendor")
            if req["category"] and row["category"].casefold() == req["category"].casefold(): reasons.append("same_category")
            if any(token in text for token in use_cases.get(row["category"], ())): reasons.append("use_case")
            if reasons and row["status"].startswith("Approved"):
                applicable = row["scope"] in ("Company-wide", department)
                matches.append({**row, "match_reasons": reasons, "scope_applicable": applicable})
                self.fact("software_catalog", f"{row['product_name']} ({row['software_id']}) is {row['status']}; scope {row['scope']}; {row['licensed_seats']} licensed seats; match: {', '.join(reasons)}. Scope {'fits' if applicable else 'requires clarification'}. Unused seat availability and feature fit are not recorded.", f"software_catalog.csv:{row['software_id']}")
        if not matches:
            self.fact("software_catalog", "No approved catalog match found by product, vendor, category, or supported use-case search; semantic coverage is limited.", "software_catalog.csv:search")
        return {"status": "ok", "matches": matches, "seat_utilization_known": False}

    def vendor_registry(self):
        vendor = next((x for x in csv_rows("vendors.csv", self.data_dir) if x["vendor_name"].casefold() == self.request["vendor_name"].casefold()), None)
        history = [x for x in csv_rows("purchase_history.csv", self.data_dir) if x["vendor_name"].casefold() == self.request["vendor_name"].casefold()]
        if vendor:
            self.fact("vendor_registry", f"Registry {vendor['vendor_name']}: procurement {vendor['procurement_status']}, security {vendor['security_status']}, review date {vendor['security_review_date'] or 'missing'}, terms {vendor['legal_terms_status']}.", f"vendors.csv:{vendor['vendor_id']}")
        else:
            self.fact("vendor_registry", "Vendor is absent from the registry; onboarding, security and legal status are unverified.", "vendors.csv:search")
        for row in history:
            self.fact("vendor_registry", f"Prior {row['status']} purchase of {row['product_name']} for {row['department']} (${float(row['annual_amount_usd']):,.2f}); this does not approve the current use case.", f"purchase_history.csv:{row['purchase_id']}")
        return {"status": "ok", "vendor": vendor, "history": history}

    def vendor_risk(self):
        if not self.request["vendor_name"]:
            raise ValueError("Vendor name missing")
        assessment = RiskAssessment.model_validate(self.risk_fetcher(self.request["vendor_name"])).model_dump()
        if assessment["vendor_name"].casefold() != self.request["vendor_name"].casefold():
            raise ValueError("Vendor identity mismatch")
        self.fact("vendor_risk", f"Service {assessment['vendor_name']}: security {assessment['security_review_status']}, last review {assessment['last_review_date'] or 'missing'}, risk {assessment['risk_level']}, outside-region storage {assessment['stores_data_outside_region']}, personal-data processing capability {assessment['processes_personal_data']}.", f"GET /vendor-risk/{self.request['vendor_name']}")
        return {"status": "ok", "assessment": assessment}

    def policy_check(self):
        policy_bytes = (self.data_dir / "procurement_policy.md").read_bytes()
        if hashlib.sha256(policy_bytes).hexdigest() != POLICY_SHA256:
            raise ValueError("Policy changed; review and update the versioned deterministic engine")
        text = policy_bytes.decode("utf-8")
        report = evaluate_policy(self.request, self.results)
        for reason in report["reasons"]:
            self.fact("policy_check", reason, "procurement_policy.md:" + reason.split(":", 1)[0])
        if report["missing_information"]:
            self.fact("policy_check", "Unverified/missing information: " + "; ".join(report["missing_information"]), "procurement_policy.md:sections 1 and 10")
        return {"status": "ok", "report": report, "policy_text": text}

    def collect(self):
        self.call("policy_check")
        return self.results
