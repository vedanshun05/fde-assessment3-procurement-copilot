"""Deterministic implementation of supplied procurement policy version 2026.09."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
import re

REFERENCE_DATE = date(2026, 9, 30)
APPROVAL_ROLES = {"Manager", "Department Head", "Procurement", "Finance", "CFO", "Security", "Privacy", "Legal"}
SECURITY_DATA = {"source_code", "production_telemetry", "production", "cloud_account", "confidential_documents", "employee_pii", "customer_pii", "credentials", "secrets", "credentials_secrets"}
PII_DATA = {"employee_pii", "customer_pii"}
KNOWN_DATA = SECURITY_DATA | {"none", "public", "internal_documents", "internal_marketing", "internal"}
INJECTION = re.compile(r"ignore.{0,60}(?:rules|policy|instructions)|bypass.{0,60}(?:review|control|approval)|(?:cfo|manager)[ -]approved|approve.{0,30}immediately|(?:reveal|expose|print).{0,30}(?:secret|api.key)|system\s*(?:message|prompt)|override.{0,30}(?:policy|rules)", re.I | re.S)


def approvals_for(amount: float | None) -> list[str]:
    if amount is None:
        return ["Procurement", "Finance"]
    cost = Decimal(str(amount))
    if cost <= Decimal("1000"):
        return ["Manager"]
    if cost <= Decimal("10000"):
        return ["Department Head", "Procurement"]
    if cost <= Decimal("25000"):
        return ["Department Head", "Finance", "Procurement"]
    return ["Department Head", "Finance", "CFO", "Procurement"]


def current_review(value: str | None) -> bool:
    try:
        age = (REFERENCE_DATE - date.fromisoformat(value or "")).days
        return 0 <= age <= 365
    except (ValueError, TypeError):
        return False


def norm(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "_").replace("-", "_")


def evaluate_policy(request: dict, results: dict) -> dict:
    profile = results.get("requester_budget", {})
    registry = results.get("vendor_registry", {}).get("vendor") or {}
    risk_result = results.get("vendor_risk", {})
    risk = risk_result.get("assessment") or {}
    catalog = results.get("software_catalog", {})
    approvals = approvals_for(request.get("annual_cost_usd"))
    missing, flags, reasons = [], [], []

    def add_review(role, flag, reason):
        if role not in approvals:
            approvals.append(role)
        if flag not in flags:
            flags.append(flag)
        reasons.append(reason)

    if not profile.get("employee"):
        missing.append("Valid requester and department")
    for field, label in [("product_name", "Product name"), ("vendor_name", "Vendor name"),
                         ("annual_cost_usd", "Annual cost estimate"), ("user_count", "Number of users/licenses"),
                         ("business_justification", "Business purpose"), ("requested_integrations", "Required integrations (or explicitly none)")]:
        if request.get(field) is None or request.get(field) == "":
            missing.append(label)
    data_level = norm(request.get("data_access_level"))
    if data_level not in KNOWN_DATA:
        missing.append("Intended data access level")
    budget = profile.get("budget")
    cost = request.get("annual_cost_usd")
    if budget is None:
        missing.append("Verified department software budget")
        add_review("Finance", "budget_unavailable", "Policy section 2: department budget could not be verified.")
    elif cost is not None and Decimal(str(cost)) > Decimal(str(budget["available_usd"])):
        add_review("Finance", "budget_insufficient", f"Policy section 2: ${cost:,.2f} exceeds available ${float(budget['available_usd']):,.2f}.")
    if catalog.get("matches"):
        flags.append("existing_tool_overlap")
        reasons.append("Policy section 3: existing approved catalog options must be considered; overlap alone does not reject a request.")
    integration_text = " ".join(request.get("requested_integrations") or []).lower()
    if data_level in SECURITY_DATA or re.search(r"production|cloud.account|source.code|git.repositor|credential|secret", integration_text):
        add_review("Security", "security_review_required", "Policy section 5: the requested data/integrations require use-case-specific Security review.")
    if data_level not in KNOWN_DATA:
        add_review("Security", "security_review_required", "Policy sections 1 and 5: intended data access is unverified.")
    registry_status = norm(registry.get("security_status"))
    api_status = norm(risk.get("security_review_status"))
    registry_current = current_review(registry.get("security_review_date"))
    api_current = current_review(risk.get("last_review_date"))
    if registry_status != "approved" or not registry_current or api_status != "approved" or not api_current:
        add_review("Security", "security_review_required", "Policy section 5: both vendor sources must show a current completed assessment.")
    if any(value and not current_review(value) for value in [registry.get("security_review_date"), risk.get("last_review_date")]) or api_status == "expired":
        flags.append("vendor_review_expired")
        reasons.append("Policy section 5: vendor review is outside the 365-day validity window or has an invalid date at snapshot 2026-09-30.")
    mapped = {"pending": "not_completed", "unknown": "unknown", "approved": "approved", "expired": "expired"}
    if registry and risk and (mapped.get(registry_status, registry_status) != api_status or (registry.get("security_review_date") or None) != (risk.get("last_review_date") or None)):
        flags.append("conflicting_vendor_evidence")
        add_review("Security", "security_review_required", "Policy section 5: registry and vendor-risk service disagree; Security must reconcile both records.")
    if risk_result.get("status") != "ok":
        flags.append("vendor_risk_unavailable")
        missing.append("Current vendor-risk assessment from the service")
        reasons.append("Policy section 10: unavailable vendor evidence cannot be inferred favorable.")
    sensitive = data_level in SECURITY_DATA
    cross_region = risk.get("stores_data_outside_region") is True and sensitive
    if data_level in PII_DATA or cross_region:
        add_review("Privacy", "privacy_review_required", "Policy section 6: employee/customer PII or sensitive data stored outside the operating region requires Privacy review.")
    new_vendor = norm(registry.get("procurement_status")) != "approved"
    if (new_vendor and cost is not None and Decimal(str(cost)) >= Decimal("10000")) or norm(registry.get("legal_terms_status")) not in {"approved", "standard"} or cross_region:
        add_review("Legal", "legal_review_required", "Policy section 7: new vendor spend >= $10,000, unapproved terms, or cross-region data processing requires Legal review.")
    if not registry:
        missing.append("Vendor onboarding and legal terms")
    # Injection detection is diagnostic only; authority never depends on recognizing an attack.
    if INJECTION.search(json.dumps({"request": request, "evidence": results}, ensure_ascii=False)):
        flags.append("prompt_injection_detected")
        reasons.append("Policy section 9: embedded control-changing text is untrusted business data and was not applied.")
    failures = [name for name, result in results.items() if result.get("status") == "error"]
    if failures:
        flags.append("tool_failure")
        reasons.append("Policy section 10: one or more evidence tools failed; manual review is required.")
    if missing:
        flags.append("missing_information")
    reasons.append("Policy section 4: minimum annual-spend approvals = " + ", ".join(approvals_for(cost)) + ".")
    reasons.append("Policy section 11: recommendations do not authorize purchases or approve exceptions.")
    return {"required_approvals": list(dict.fromkeys(approvals)), "missing_information": list(dict.fromkeys(missing)),
            "risk_flags": list(dict.fromkeys(flags)), "reasons": reasons, "human_review_required": True,
            "reference_date": REFERENCE_DATE.isoformat(), "policy_version": "2026.09"}
