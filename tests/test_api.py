"""HTTP API used by the React front end."""
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)
Q2 = "20 people, 4 hours, coffee and lunch are required. Total budget €850."


def test_health_and_cases():
    assert client.get("/api/health").json()["ok"] is True
    assert len(client.get("/api/cases").json()) == 16
    assert len(client.get("/api/baseline").json()) == 16


def test_analyse_matches_engine():
    d = client.post("/api/analyse", json={"enquiry": Q2, "use_llm": False}).json()
    assert d["status"] == "INFEASIBLE" and d["package"]["total_eur"] == 940 and d["budget_margin_eur"] == -90
    assert d["client_draft_markdown"].startswith("**DRAFT")
    assert all(a["trade_offs"] for a in d["alternatives"])


def test_empty_enquiry_rejected():
    assert client.post("/api/analyse", json={"enquiry": ""}).status_code == 422


def test_eval_endpoint_all_pass():
    sets = client.post("/api/eval").json()["sets"]
    assert all(s["passed"] == s["total"] for s in sets.values()) and sum(s["total"] for s in sets.values()) == 36
