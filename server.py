from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from src.contracts import PurchaseRequest, ProcurementDecision
from src.data_access import load_requests
from src.solution import analyze_request
from src.providers import live_configuration
from src.tools import DATA_DIR, csv_rows

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Procure | Procurement Request Copilot", version="1.0.0")
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


class AnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: PurchaseRequest
    architecture: Literal["single", "staged"] = "single"
    mode: Literal["offline", "live"] = "offline"


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "procurement-copilot"}


@app.get("/api/bootstrap")
def bootstrap():
    config = live_configuration()
    return {"requests": load_requests(), "employees": csv_rows("employees.csv", DATA_DIR),
            "live_available": config.configured, "live_provider": config.provider, "live_model": config.model,
            "default_mode": os.getenv("COPILOT_MODE", "offline"),
            "reference_date": "2026-09-30", "policy_version": "2026.09"}


@app.post("/api/analyze", response_model=ProcurementDecision)
def analyze(body: AnalysisInput):
    if body.mode == "live" and not live_configuration().configured:
        raise HTTPException(400, "Live AI is not configured. Use the offline demo or configure the server's .env.")
    try:
        return analyze_request(body.request, body.architecture, body.mode)
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, "The request could not be analyzed. Check its fields and try again.") from exc


@app.middleware("http")
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return response
