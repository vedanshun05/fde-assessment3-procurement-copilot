"""Gemini generateContent REST adapter with bounded tools and structured outputs."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import os
import re
import threading
import time

import httpx

from src.agents import SYSTEM
from src.contracts import AgentProposal, AnalystAssessment
from src.providers import ModelRateLimitError, live_configuration

_pace_lock = threading.Lock()
_next_call_at = 0.0


def pace_call() -> float:
    """Space model requests within this process, including both agent stages."""
    global _next_call_at
    interval = float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "6"))
    if not math.isfinite(interval) or not 0 <= interval <= 60:
        raise ValueError("GEMINI_MIN_INTERVAL_SECONDS must be between 0 and 60")
    if interval == 0:
        return 0.0
    with _pace_lock:
        now = time.monotonic()
        wait = max(0.0, _next_call_at - now)
        _next_call_at = max(now, _next_call_at) + interval
    time.sleep(wait)
    return round(wait * 1000, 3)


class GeminiAgent:
    def __init__(self, telemetry, client=None):
        config = live_configuration()
        self.key = os.getenv("GEMINI_API_KEY", "").strip()
        if not self.key and client is None:
            raise ValueError("GEMINI_API_KEY is not configured")
        self.model = config.model
        if not re.fullmatch(r"[A-Za-z0-9._-]+", self.model):
            raise ValueError("Invalid Gemini model identifier")
        self.telemetry = telemetry
        self.telemetry.provider = "gemini"
        self.telemetry.model = self.model
        self.client = client

    def call(self, stage, contents, *, tools=None, schema=None):
        pacing_ms = pace_call()
        started = time.perf_counter()
        self.telemetry.llm_calls = (self.telemetry.llm_calls or 0) + 1
        trace = {"stage": stage, "status": "error", "pacing_ms": pacing_ms}
        body = {"systemInstruction": {"parts": [{"text": SYSTEM}]},
                "contents": contents, "generationConfig": {"maxOutputTokens": 4096}}
        if tools is not None:
            declarations = [{"name": item["name"], "description": item["description"],
                             "parametersJsonSchema": item["parameters"]} for item in tools]
            body["tools"] = [{"functionDeclarations": declarations}]
            body["toolConfig"] = {"functionCallingConfig": {"mode": "ANY"}}
        if schema is not None:
            body["generationConfig"].update(responseMimeType="application/json", responseJsonSchema=schema.model_json_schema())
        try:
            post = self.client.post if self.client is not None else httpx.post
            response = post(f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                            headers={"x-goog-api-key": self.key}, json=body, timeout=30.0)
            trace["http_status"] = response.status_code
            if response.status_code == 429:
                trace["status"] = "rate_limited"
                raise ModelRateLimitError("Gemini free-tier quota is temporarily unavailable")
            response.raise_for_status()
            result = response.json()
            usage = result.get("usageMetadata", {})
            self.telemetry.input_tokens += usage.get("promptTokenCount", 0)
            self.telemetry.output_tokens += usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
            candidates = result.get("candidates", [])
            if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
                raise ValueError("Gemini refused or did not finish the assessment")
            content = candidates[0].get("content", {})
            if content.get("role") != "model" or not content.get("parts"):
                raise ValueError("Gemini returned no model content")
            trace["status"] = "ok"
            return content
        finally:
            trace["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
            self.telemetry.model_trace.append(trace)

    def gather(self, tools, stage):
        contents = [{"role": "user", "parts": [{"text": json.dumps({"untrusted_request": tools.request})}]}]
        for _ in range(2):
            pending = [item for item in tools.schemas if item["name"] not in tools.results]
            if not pending:
                break
            content = self.call(stage, contents, tools=pending)
            calls = [part["functionCall"] for part in content["parts"] if "functionCall" in part]
            if not calls or len(calls) > 10:
                raise ValueError("Invalid or unbounded Gemini tool plan")
            # Preserve opaque thought signatures and optional call IDs for subsequent turns.
            contents.append(content)
            responses = []
            for call in calls:
                if call["name"] not in {item["name"] for item in pending}:
                    raise ValueError("Gemini invoked an undeclared tool")
                result = tools.call(call["name"], call.get("args", {}))
                response = {"name": call["name"], "response": result}
                if "id" in call:
                    response["id"] = call["id"]
                responses.append({"functionResponse": response})
            contents.append({"role": "user", "parts": responses})
        tools.collect()
        return contents

    def structured(self, tools, schema, stage, extra=None, conversation=None):
        payload = {"untrusted_request": tools.request, "tool_results": tools.results,
                   "evidence_ledger": [e.model_dump() for e in tools.evidence], "untrusted_previous_stage": extra}
        contents = deepcopy(conversation or [])
        part = {"text": "Return the requested structured assessment using this evidence package.\n" + json.dumps(payload)}
        if contents and contents[-1]["role"] == "user":
            contents[-1]["parts"].append(part)
        else:
            contents.append({"role": "user", "parts": [part]})
        content = self.call(stage, contents, schema=schema)
        if any("functionCall" in part for part in content["parts"]):
            raise ValueError("Unexpected tool call during structured assessment")
        text = "".join(part.get("text", "") for part in content["parts"] if not part.get("thought", False))
        return schema.model_validate_json(text)

    def single(self, tools):
        conversation = self.gather(tools, "procurement_agent")
        return self.structured(tools, AgentProposal, "procurement_agent", conversation=conversation)

    def staged(self, tools):
        conversation = self.gather(tools, "procurement_analyst")
        assessment = self.structured(tools, AnalystAssessment, "procurement_analyst", conversation=conversation)
        proposal = self.structured(tools, AgentProposal, "policy_risk_reviewer", extra=assessment.model_dump())
        return proposal, assessment
