from fastapi.testclient import TestClient

from server import app


def test_bootstrap_does_not_expose_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","test-secret-never-expose")
    with TestClient(app) as client:
        response=client.get("/api/bootstrap")
    assert response.status_code==200
    assert response.json()["live_available"] is True
    assert "test-secret-never-expose" not in response.text
    assert response.headers["content-security-policy"].startswith("default-src 'self'")


def test_invalid_api_request_rejected():
    with TestClient(app) as client:
        response=client.post("/api/analyze",json={"request":{"annual_cost_usd":-1}})
    assert response.status_code==422


def test_live_mode_without_credentials_does_not_silently_simulate(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY",raising=False)
    with TestClient(app) as client:
        response=client.post("/api/analyze",json={"mode":"live","request":{}})
    assert response.status_code==400
