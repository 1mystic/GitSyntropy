from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_compatibility_full_data_contract() -> None:
    response = client.post(
        "/api/v1/compatibility/run",
        json={"member_a": "alice", "member_b": "bob", "data_mode": "full"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["member_a"] == "alice"
    assert payload["member_b"] == "bob"
    assert payload["total_score_36"] <= 36
    assert payload["score_pct_100"] <= 100
    assert 0.5 <= payload["confidence"] <= 1.0
    assert len(payload["dimension_breakdown"]) == 8
    assert set(payload["dimension_scores"]) == {
        "innovation_drive",
        "leadership_orientation",
        "team_resilience",
        "work_style",
        "decision_style",
        "risk_tolerance",
        "stress_response",
        "chronotype_sync",
    }


def test_compatibility_incomplete_data_flags_risk() -> None:
    response = client.post(
        "/api/v1/compatibility/run",
        json={"member_a": "night-architect", "member_b": "early-ops", "data_mode": "incomplete"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["confidence"] < 1.0
    assert len(payload["data_gaps"]) >= 1
    assert any("Low confidence" in flag for flag in payload["risk_flags"])
