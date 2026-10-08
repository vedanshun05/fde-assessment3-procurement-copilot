"""Native Gemini REST orchestration tests; no model quality claims or live calls."""
import json
import sys

from fastapi.testclient import TestClient
import httpx
import pytest

from server import app
from src.data_access import get_request
from src.providers import live_configuration
from src.solution import analyze_request
from src.tools import DATA_DIR


def fixture_risk(vendor):
    records = json.loads((DATA_DIR / "vendor_risk.json").read_text())
    return {"vendor_name": vendor, **records[vendor]}


def configure(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "local-test-key-never-expose")


class GeminiTransport:
    def __init__(self, variant="normal"):
        self.variant = variant
        self.bodies = []

    def __call__(self, request):
        assert request.url.host == "generativelanguage.googleapis.com"
        assert "key=" not in str(request.url)
        assert request.headers["x-goog-api-key"] == "local-test-key-never-expose"
        body = json.loads(request.content)
        self.bodies.append(body)
        if self.variant == "quota":
            return httpx.Response(429, json={"error": {"message": "local-test-key-never-expose"}})
        if self.variant == "unauthorized":
            return httpx.Response(403, json={"error": {"message": "local-test-key-never-expose"}})
        if self.variant == "timeout":
            raise httpx.ReadTimeout("local-test-key-never-expose", request=request)
        if "tools" in body:
            names = [item["name"] for item in body["tools"][0]["functionDeclarations"]]
            assert body["toolConfig"]["functionCallingConfig"]["mode"] == "ANY"
            name = "purchase_now" if self.variant == "unknown_tool" else "policy_check"
            if self.variant == "partial_retrieval":
                name = names[0]
            args = {"endpoint": "https://attacker.example"} if self.variant == "invalid_arguments" else {}
            parts = [{"functionCall": {"id": f"call-{len(self.bodies)}", "name": name, "args": args}, "thoughtSignature": "opaque-signature"}]
        else:
            payload = json.loads(body["contents"][-1]["parts"][-1]["text"].split("\n", 1)[1])
            ids = [item["evidence_id"] for item in payload["evidence_ledger"]]
            if self.variant == "bad_citation":
                ids = ["FABRICATED"]
            schema = body["generationConfig"]["responseJsonSchema"]
            assert body["generationConfig"]["responseMimeType"] == "application/json"
            if schema["title"] == "AnalystAssessment":
                value = {"need_summary": "Training", "credible_gap": True, "gap_explanation": "Training service", "evidence_ids": ids, "concerns": []}
            else:
                value = {"action": "route_for_reviews", "rationale": "Prepare required reviews.", "evidence_ids": ids,
                         "additional_approvals": [], "additional_missing_information": [], "additional_risk_flags": [], "credible_gap": True}
                if self.variant == "approval_claim":
                    value["rationale"] = "The purchase is approved"
            if self.variant == "invalid_schema":
                value = {"action": "buy_now"}
            # Thoughts are excluded from the structured result, but counted in usage.
            parts = [{"text": "internal deliberation", "thought": True}, {"text": json.dumps(value)}]
        finish = "SAFETY" if self.variant == "refusal" else "MAX_TOKENS" if self.variant == "truncated" else "STOP"
        return httpx.Response(200, json={"candidates": [{"finishReason": finish, "content": {"role": "model", "parts": parts}}],
                                       "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "thoughtsTokenCount": 2}})


@pytest.mark.parametrize("architecture,calls", [("single", 2), ("staged", 3)])
def test_gemini_tools_json_and_fresh_reviewer(monkeypatch, architecture, calls):
    configure(monkeypatch)
    transport = GeminiTransport()
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        decision = analyze_request(get_request("REQ-1010"), architecture, "live", risk_fetcher=fixture_risk, model_client=client)
    assert "model_unavailable" not in decision.risk_flags
    assert decision.telemetry.provider == "gemini"
    assert decision.telemetry.model == "gemini-3.5-flash-lite"
    assert decision.telemetry.llm_calls == calls
    assert decision.telemetry.tool_calls == 5
    assert decision.telemetry.input_tokens == calls * 10
    assert decision.telemetry.output_tokens == calls * 7
    second = transport.bodies[1]["contents"]
    assert [item["role"] for item in second] == ["user", "model", "user"]
    assert second[1]["parts"][0]["thoughtSignature"] == "opaque-signature"
    assert second[2]["parts"][0]["functionResponse"]["id"] == "call-1"
    if architecture == "staged":
        assert len(transport.bodies[-1]["contents"]) == 1
        assert decision.analyst_assessment
    assert "local-test-key-never-expose" not in decision.model_dump_json()


@pytest.mark.parametrize("variant,flag", [("quota", "model_rate_limited"), ("unauthorized", "model_unavailable"),
    ("timeout", "model_unavailable"), ("refusal", "model_unavailable"), ("truncated", "model_unavailable"),
    ("invalid_schema", "model_unavailable"), ("unknown_tool", "model_unavailable"), ("invalid_arguments", "model_unavailable"),
    ("bad_citation", "ungrounded_model_output"), ("approval_claim", "approval_claim_blocked")])
def test_gemini_failures_preserve_controls_and_hide_key(monkeypatch, variant, flag):
    configure(monkeypatch)
    transport = GeminiTransport(variant)
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        decision = analyze_request(get_request("REQ-1010"), "single", "live", risk_fetcher=fixture_risk, model_client=client)
    assert flag in decision.risk_flags
    assert decision.action == "manual_review"
    assert "Manager" in decision.required_approvals
    assert decision.telemetry.tool_calls == 5
    assert "local-test-key-never-expose" not in decision.model_dump_json()
    if variant == "quota":
        assert len(transport.bodies) == 1
        assert decision.telemetry.model_trace[0]["status"] == "rate_limited"


def test_two_round_limit_completes_missing_tool_coverage_in_code(monkeypatch):
    configure(monkeypatch)
    transport = GeminiTransport("partial_retrieval")
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        decision = analyze_request(get_request("REQ-1010"), "single", "live", risk_fetcher=fixture_risk, model_client=client)
    assert len(transport.bodies) == 3
    assert decision.telemetry.tool_calls == 5
    assert "model_unavailable" not in decision.risk_flags


def test_provider_auto_selection_and_explicit_precedence(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER")
    monkeypatch.setenv("GEMINI_API_KEY", "local-test-key-never-expose")
    assert live_configuration().provider == "gemini"
    monkeypatch.setenv("OPENAI_API_KEY", "another-local-test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    assert live_configuration().provider == "openai"
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY")
    assert live_configuration().configured is False


def test_gemini_bootstrap_never_exposes_key(monkeypatch):
    configure(monkeypatch)
    with TestClient(app) as client:
        response = client.get("/api/bootstrap")
    assert response.json()["live_available"] is True
    assert response.json()["live_provider"] == "gemini"
    assert "local-test-key-never-expose" not in response.text


def test_eval_stops_on_quota_and_marks_partial_results(monkeypatch, tmp_path):
    from evals import compare
    configure(monkeypatch)
    transport = GeminiTransport("quota")
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        real_analyze = analyze_request
        monkeypatch.setattr(compare, "analyze_request", lambda request, architecture, mode, **kwargs:
                            real_analyze(request, architecture, mode, risk_fetcher=fixture_risk, model_client=client))
        monkeypatch.setattr(sys, "argv", ["compare.py", "--mode", "live", "--repeat", "1", "--output", str(tmp_path)])
        with pytest.raises(SystemExit) as error:
            compare.main()
    assert error.value.code == 1
    assert len(transport.bodies) == 1
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["comparison_complete"] is False
    assert summary["halt_reason"] == "provider_rate_limit"
    assert summary["provider"] == "gemini"
    assert summary["architectures"]["single"]["runs"] == 1
    assert summary["architectures"]["staged"]["runs"] == 0
