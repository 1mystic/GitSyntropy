from fastapi.testclient import TestClient
from time import sleep

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_mock_analysis() -> None:
    response = client.post("/api/v1/analysis/mock", json={"team_id": "team_alpha"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["team_id"] == "team_alpha"
    assert "score" in payload


def test_github_sync_lifecycle() -> None:
    start = client.post("/api/v1/github/sync", json={"github_handle": "night-architect", "user_id": "user_1"})
    assert start.status_code == 200
    started_payload = start.json()
    assert started_payload["status"] in {"queued", "syncing"}
    assert started_payload["activity_rhythm_score"] > 0

    sync_id = started_payload["sync_id"]
    in_flight = client.get(f"/api/v1/github/sync/{sync_id}")
    assert in_flight.status_code == 200
    assert in_flight.json()["status"] in {"queued", "syncing", "complete"}

    sleep(2.8)
    complete = client.get(f"/api/v1/github/sync/{sync_id}")
    assert complete.status_code == 200
    completed_payload = complete.json()
    assert completed_payload["status"] == "complete"
    assert completed_payload["completed_at"] is not None


def test_assessment_questions_cover_required_dimensions() -> None:
    response = client.get("/api/v1/assessment/questions")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 8
    assert payload[0]["id"] == "q1"
    assert payload[-1]["id"] == "q8"


def test_assessment_submit_and_profile_roundtrip() -> None:
    submit = client.post(
        "/api/v1/assessment/responses",
        json={
            "user_id": "user_iter4",
            "answers": {
                "q1": 1,
                "q2": 2,
                "q3": 3,
                "q4": 4,
                "q5": 5,
                "q6": 1,
                "q7": 4,
                "q8": 5,
            },
        },
    )
    assert submit.status_code == 200
    submit_payload = submit.json()
    assert submit_payload["complete"] is True
    assert submit_payload["missing_question_ids"] == []
    assert submit_payload["answered_count"] == 8
    assert submit_payload["total_questions"] == 8
    assert submit_payload["scores"]["nadi_chronotype_sync"] > 0
    assert submit_payload["submitted_at"] is not None

    profile = client.get("/api/v1/assessment/responses/user_iter4")
    assert profile.status_code == 200
    profile_payload = profile.json()
    assert profile_payload["user_id"] == "user_iter4"
    assert profile_payload["complete"] is True
    assert profile_payload["scores"] == submit_payload["scores"]


def test_assessment_submit_requires_answer_range() -> None:
    response = client.post(
        "/api/v1/assessment/responses",
        json={
            "user_id": "user_iter4_invalid",
            "answers": {"q1": 0},
        },
    )
    assert response.status_code == 422


def test_orchestrator_run_stores_candidate_step() -> None:
    response = client.post(
        "/api/v1/orchestrator/run",
        json={"team_id": "team_iter6", "user_id": "user_iter6", "include_candidates": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "started"
    assert payload["steps"] == [
        "github_analyst",
        "psychometric_profiler",
        "candidate_simulation",
        "compatibility_engine",
        "synthesis",
    ]
    assert payload["run_id"]


def test_analysis_websocket_streams_orchestrator_events() -> None:
    run = client.post(
        "/api/v1/orchestrator/run",
        json={"team_id": "team_iter6_stream", "user_id": "user_stream", "include_candidates": True},
    )
    assert run.status_code == 200
    run_id = run.json()["run_id"]

    with client.websocket_connect(f"/ws/analysis/{run_id}") as ws:
        received: list[dict] = []
        while True:
            event = ws.receive_json()
            received.append(event)
            # Token events don't carry "step"; skip but continue reading
            if event.get("type") == "synthesis_token":
                continue
            if event.get("step") == "orchestration" and event.get("status") == "completed":
                break

    step_events = [e for e in received if "step" in e]
    assert step_events, "Expected step events from orchestrator websocket."

    completed_steps = {e["step"] for e in step_events if e.get("status") == "completed"}
    assert "candidate_simulation" in completed_steps
    assert "synthesis" in completed_steps
    assert "orchestration" in completed_steps
