"""Targeted tests to cover remaining uncovered paths in main.py and services.py."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import (
    assessment_questions,
    build_assessment_profile,
    cat_select_next_question,
    compatibility,
    mock_compatibility_scores,
    score_assessment,
    synthesis_from_compat,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# main.py — paths not yet covered
# ---------------------------------------------------------------------------


def test_github_sync_status_not_found() -> None:
    resp = client.get("/api/v1/github/sync/00000000-0000-0000-0000-nonexistent")
    assert resp.status_code == 404


def test_insights_synthesis_endpoint() -> None:
    resp = client.get("/api/v1/insights/synthesis")
    assert resp.status_code == 200
    payload = resp.json()
    assert "narrative" in payload
    assert "recommendations" in payload
    assert "uncertainty_note" in payload


def test_orchestrator_run_without_candidates() -> None:
    resp = client.post(
        "/api/v1/orchestrator/run",
        json={"team_id": "team_solo", "user_id": "user_solo", "include_candidates": False},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "candidate_simulation" not in payload["steps"]


def test_assessment_submit_endpoint_alias() -> None:
    """POST /assessment/submit (alias) should work identically to /assessment/responses."""
    resp = client.post(
        "/api/v1/assessment/submit",
        json={
            "user_id": "user_alias_test",
            "answers": {"q1": 3, "q2": 3, "q3": 3, "q4": 3, "q5": 3, "q6": 3, "q7": 3, "q8": 3},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["complete"] is True


def test_session_invalid_token_returns_401() -> None:
    resp = client.get("/api/v1/auth/session", headers={"Authorization": "Bearer not.a.valid.jwt"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# services.py — uncovered branches
# ---------------------------------------------------------------------------


def test_score_assessment_missing_question_defaults_zero() -> None:
    """Missing question ID → score defaults to 0.0 for that dimension."""
    scores = score_assessment({"q1": 5})  # only q1 answered
    from app.schemas import ASHTAKOOT_DIMENSIONS
    for i, dim in enumerate(ASHTAKOOT_DIMENSIONS):
        if i == 0:  # q1 answered
            assert scores[dim] > 0
        else:  # rest unanswered
            assert scores[dim] == 0.0


def test_build_assessment_profile_incomplete() -> None:
    profile = build_assessment_profile("user_inc", answers={"q1": 3, "q2": 4})
    assert profile["complete"] is False
    assert len(profile["missing_question_ids"]) == 6


def test_synthesis_from_compat_excellent() -> None:
    r = synthesis_from_compat(total_score=30.0, weak_dimensions=[])
    assert "strong" in r["narrative"].lower() or "excellent" in r["narrative"].lower() or "alignment" in r["narrative"].lower()
    assert r["uncertainty_note"] == "No high-risk weak dimensions detected in this run."


def test_synthesis_from_compat_poor() -> None:
    r = synthesis_from_compat(total_score=10.0, weak_dimensions=["nadi_chronotype_sync", "bhakoot_strategy"])
    assert "friction" in r["narrative"].lower()
    assert "nadi_chronotype_sync" in r["uncertainty_note"]


def test_synthesis_from_compat_workable() -> None:
    r = synthesis_from_compat(total_score=22.0, weak_dimensions=[])
    assert "workable" in r["narrative"].lower() or "ritual" in r["narrative"].lower()


def test_compatibility_chronotype_risk_flag() -> None:
    """Very low nadi score triggers the chronotype-specific risk flag."""
    from app.schemas import ASHTAKOOT_WEIGHTS
    scores_a = {dim: w * 0.9 for dim, w in ASHTAKOOT_WEIGHTS.items()}
    scores_b = {dim: w * 0.9 for dim, w in ASHTAKOOT_WEIGHTS.items()}
    # Drive nadi scores apart to force the chronotype risk flag
    scores_a["nadi_chronotype_sync"] = ASHTAKOOT_WEIGHTS["nadi_chronotype_sync"] * 0.9
    scores_b["nadi_chronotype_sync"] = ASHTAKOOT_WEIGHTS["nadi_chronotype_sync"] * 0.05
    result = compatibility(scores_a, scores_b)
    assert any("Chronotype" in flag for flag in result["risk_flags"])


def test_mock_compatibility_incomplete_mode() -> None:
    scores = mock_compatibility_scores("test_user", data_mode="incomplete")
    none_count = sum(1 for v in scores.values() if v is None)
    assert none_count == 3


def test_assessment_questions_dimensions_match() -> None:
    """Each question should map to a valid Ashtakoot dimension."""
    from app.schemas import ASHTAKOOT_DIMENSIONS
    questions = assessment_questions()
    assert len(questions) == 8
    dims = [q["dimension"] for q in questions]
    assert dims == ASHTAKOOT_DIMENSIONS


def test_cat_select_next_ordered_by_weight() -> None:
    """Sequential calls should return questions in weight-descending order."""
    answered = {}
    order = []
    for _ in range(8):
        nxt = cat_select_next_question(answered)
        if nxt is None:
            break
        order.append(nxt)
        answered[nxt] = 3
    # First 5 should be q8,q7,q6,q5,q4 (weights 8,7,6,5,4 ≥ 4 → triggers early stop)
    assert order[0] == "q8"
    assert order[1] == "q7"
    assert order[2] == "q6"
