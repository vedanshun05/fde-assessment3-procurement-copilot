from __future__ import annotations

import time
import re
from src.contracts import Architecture, ProcurementDecision, PurchaseRequest, RunTelemetry
from src.data_access import get_request
from src.agents import make_live_agent, offline_proposal, offline_staged
from src.policy import APPROVAL_ROLES
from src.tools import ToolSet

LABELS = {"request_information": "Request clarification", "check_existing_tool": "Check an existing tool first",
          "route_for_reviews": "Route for required human reviews", "manual_review": "Hold for manual evidence review"}


def analyze_request(request: PurchaseRequest | dict, architecture: Architecture = "single", mode: str = "offline", *, risk_fetcher=None, data_dir=None, model_client=None) -> ProcurementDecision:
    if architecture not in {"single", "staged"}:
        raise ValueError("Architecture must be single or staged")
    if mode not in {"offline", "live"}:
        raise ValueError("Mode must be offline or live")
    request = PurchaseRequest.model_validate(request)
    started = time.perf_counter()
    stages = ["procurement_agent"] if architecture == "single" else ["procurement_analyst", "policy_risk_reviewer"]
    tel = RunTelemetry(llm_calls=0, tool_calls=0, mode=mode, agent_stages=stages)
    kwargs = {"risk_fetcher": risk_fetcher}
    if data_dir is not None: kwargs["data_dir"] = data_dir
    tools = ToolSet(request, tel, **kwargs)
    model_error = None
    assessment = None
    try:
        if architecture == "single":
            proposal = make_live_agent(tel, model_client).single(tools) if mode == "live" else offline_proposal(tools)
        else:
            proposal, assessment = make_live_agent(tel, model_client).staged(tools) if mode == "live" else offline_staged(tools)
    except Exception as exc:
        if mode == "offline":
            raise
        model_error = type(exc).__name__
        proposal = offline_proposal(tools)
    report = tools.results.get("policy_check", {}).get("report")
    if report is None:
        report = {"required_approvals": ["Procurement", "Finance", "Security"],
                  "missing_information": ["Verified procurement policy and material evidence"],
                  "risk_flags": ["policy_unavailable", "tool_failure", "missing_information"]}
    approvals = list(report["required_approvals"])
    flags = list(report["risk_flags"])
    missing = list(report["missing_information"])
    action = proposal.action
    rationale = proposal.rationale[:2000]
    ledger = {e.evidence_id: e for e in tools.evidence}
    bad_evidence = not proposal.evidence_ids or any(e not in ledger for e in proposal.evidence_ids)
    if assessment is not None and (not assessment.evidence_ids or any(e not in ledger for e in assessment.evidence_ids)):
        bad_evidence = True
    if bad_evidence:
        flags.append("ungrounded_model_output")
        action = "manual_review"
        rationale = "The model cited unsupported evidence. The original tool evidence is preserved for manual review."
    if re.search(r"(?:purchase|request|spend|exception)\s+(?:is\s+|has been\s+)?(?:approved|authorized)|(?:i|we)\s+(?:approved|purchased)|cfo[ -]approved", rationale, re.I):
        flags.append("approval_claim_blocked")
        action = "manual_review"
        rationale = "The assessment claimed approval without a verified human decision. All required human reviews remain pending."
    for role in proposal.additional_approvals:
        if role in APPROVAL_ROLES and role not in approvals: approvals.append(role)
    # Additional uncertainty may add controls but can never relax the deterministic floor.
    missing.extend(x[:300] for x in proposal.additional_missing_information[:20])
    flags.extend(x[:100] for x in proposal.additional_risk_flags[:20])
    if model_error:
        flags.append("model_unavailable")
        if model_error == "ModelRateLimitError":
            flags.append("model_rate_limited")
        action = "manual_review"
        rationale = f"Live model assessment failed ({model_error}). Deterministic evidence and required reviews are retained; a human must complete the assessment."
    if "vendor_risk_unavailable" in flags or "tool_failure" in flags:
        action = "manual_review"
    elif missing and action != "manual_review":
        action = "request_information"
    elif any(x in flags for x in ("budget_insufficient", "security_review_required", "privacy_review_required", "legal_review_required", "vendor_review_expired", "conflicting_vendor_evidence")) and action not in {"manual_review", "request_information"}:
        action = "route_for_reviews"
    if action == "request_information":
        next_step = "Ask the requester for: " + "; ".join(dict.fromkeys(missing)) + ". Then rerun and route to " + ", ".join(approvals) + "."
    elif action == "check_existing_tool":
        next_step = "Procurement must verify feature fit, permitted data use, scope and unused license availability. If a new purchase is needed, obtain " + ", ".join(approvals) + " approval."
    elif action == "manual_review":
        next_step = "Hold the purchase. Send the evidence package and unresolved information to " + ", ".join(approvals) + " for manual verification and human approvals."
    else:
        next_step = "Send the request and evidence package to " + ", ".join(approvals) + "; resolve all listed risks and any catalog overlap before a human authorizes purchase."
    tel.latency_ms = round((time.perf_counter()-started)*1000, 3)
    return ProcurementDecision(request_id=request.request_id, recommendation=LABELS[action], action=action,
        rationale=rationale, evidence=tools.evidence, required_approvals=approvals,
        missing_information=list(dict.fromkeys(missing)), risk_flags=list(dict.fromkeys(flags)), next_step=next_step,
        human_review_required=True, telemetry=tel, architecture=architecture,
        analyst_assessment=assessment.model_dump() if assessment else None)


def handle_request(request_id: str, architecture: Architecture = "single") -> ProcurementDecision:
    """Assessment adapter.

    Keep this function callable by the public/hidden evaluation harness.
    Your internal implementation may use any framework, modules, agents, tools,
    deterministic checks, or orchestration strategy.
    """
    import os
    return analyze_request(get_request(request_id), architecture, os.getenv("COPILOT_MODE", "offline"))
