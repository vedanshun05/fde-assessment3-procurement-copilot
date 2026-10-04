from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class EvidenceItem(BaseModel):
    evidence_id: str | None = None
    source: str = Field(description="Tool/data source name")
    finding: str = Field(description="Concise factual finding")
    reference: str | None = Field(default=None, description="Optional record ID / policy section / endpoint")


class RunTelemetry(BaseModel):
    llm_calls: int | None = None
    tool_calls: int | None = None
    tool_names: list[str] = Field(default_factory=list)
    mode: str = "offline"
    model: str | None = None
    latency_ms: float = 0
    input_tokens: int = 0
    output_tokens: int = 0
    agent_stages: list[str] = Field(default_factory=list)
    tool_trace: list[dict] = Field(default_factory=list)
    model_trace: list[dict] = Field(default_factory=list)


class ProcurementDecision(BaseModel):
    request_id: str
    recommendation: str = Field(description="Short recommendation label or sentence")
    evidence: list[EvidenceItem] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    next_step: str
    human_review_required: bool = True
    telemetry: RunTelemetry | None = None
    action: str = "manual_review"
    rationale: str = ""
    architecture: str = "single"
    policy_version: str = "2026.09"
    reference_date: str = "2026-09-30"
    review_status: str = "awaiting_human_review"
    analyst_assessment: dict | None = None


class PurchaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True, allow_inf_nan=False)
    request_id: str = Field(default="REQ-CUSTOM", min_length=1, max_length=100)
    requester_id: str = Field(default="", max_length=100)
    product_name: str = Field(default="", max_length=200)
    vendor_name: str = Field(default="", max_length=200)
    category: str = Field(default="", max_length=200)
    annual_cost_usd: float | None = Field(default=None, ge=0, le=1_000_000_000)
    user_count: int | None = Field(default=None, gt=0, le=1_000_000)
    business_justification: str = Field(default="", max_length=5000)
    data_access_level: str = Field(default="unknown", max_length=200)
    requested_integrations: list[str] | None = Field(default=None, max_length=30)
    urgency: str = Field(default="normal", max_length=100)

    @field_validator("annual_cost_usd")
    @classmethod
    def exact_cents(cls, value):
        from decimal import Decimal
        if value is not None and Decimal(str(value)) != Decimal(str(value)).quantize(Decimal("0.01")):
            raise ValueError("Annual cost must have at most two decimal places")
        return value

    @field_validator("requested_integrations")
    @classmethod
    def bounded_integrations(cls, value):
        if value is not None and any(not x.strip() or len(x) > 200 for x in value):
            raise ValueError("Integrations must be nonempty strings of at most 200 characters")
        return value


Action = Literal["request_information", "check_existing_tool", "route_for_reviews", "manual_review"]


class AgentProposal(BaseModel):
    """Models select ledger IDs, never author evidence or authorize purchases."""
    action: Action
    rationale: str
    evidence_ids: list[str]
    additional_approvals: list[str]
    additional_missing_information: list[str]
    additional_risk_flags: list[str]
    credible_gap: bool


class AnalystAssessment(BaseModel):
    need_summary: str
    credible_gap: bool
    gap_explanation: str
    evidence_ids: list[str]
    concerns: list[str]


Architecture = Literal["single", "staged"]

# Suggested approval names for consistency in evaluation:
# Manager, Department Head, Procurement, Finance, CFO, Security, Privacy, Legal
#
# Suggested risk-flag taxonomy (you may add others):
# existing_tool_overlap
# budget_insufficient
# security_review_required
# privacy_review_required
# legal_review_required
# vendor_review_expired
# conflicting_vendor_evidence
# vendor_risk_unavailable
# prompt_injection_detected
# missing_information
