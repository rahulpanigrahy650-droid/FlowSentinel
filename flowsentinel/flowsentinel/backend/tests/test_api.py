"""End-to-end API test on SQLite. Skipped automatically when the web stack is not installed."""
import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("langgraph")
pytest.importorskip("pydantic_settings")

os.environ.update(DATABASE_URL="sqlite:///./test_flowsentinel.db", LLM_PROVIDER="none",
                  EMBEDDING_PROVIDER="hashing", AUTO_SEED="true")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    if os.path.exists("test_flowsentinel.db"):
        os.remove("test_flowsentinel.db")
    with TestClient(app) as c:
        yield c
    if os.path.exists("test_flowsentinel.db"):
        os.remove("test_flowsentinel.db")


def test_health_and_seeded_knowledge_base(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert len(client.get("/api/knowledge/documents").json()) >= 10


def test_incident_lifecycle(client):
    r = client.post("/api/incidents", json={"title": "VPN disconnects every 10 minutes",
                                             "description": "GlobalProtect drops every 10 minutes at home."})
    assert r.status_code == 201
    inc = client.get(f"/api/incidents/{r.json()['id']}").json()
    assert inc["analysis_status"] == "done" and inc["category"] == "network"
    assert inc["analysis"]["passages"] and inc["suggested_resolution"]

    patched = client.patch(f"/api/incidents/{inc['id']}", json={
        "status": "resolved", "resolution_notes": "Switched the client to SSL mode; drops stopped.",
        "save_to_kb": True}).json()
    assert patched["status"] == "resolved" and patched["resolved_at"]
    titles = [d["title"] for d in client.get("/api/knowledge/documents").json()]
    assert any(t.startswith("Resolved #") for t in titles)

    summary = client.get("/api/analytics/summary").json()
    assert summary["totals"]["resolved"] == 1 and summary["mttr_hours"] is not None


def test_critical_incident_escalates_and_filters(client):
    client.post("/api/incidents", json={"title": "Production database down",
                                         "description": "All users cannot login, postgres primary not responding"})
    items = client.get("/api/incidents", params={"severity": "critical", "status": "escalated"}).json()
    assert items["total"] >= 1 and items["items"][0]["assigned_team"] == "Database Administration"


def test_validation_and_404(client):
    assert client.post("/api/incidents", json={"title": "x", "description": "y"}).status_code == 422
    assert client.get("/api/incidents/99999").status_code == 404
