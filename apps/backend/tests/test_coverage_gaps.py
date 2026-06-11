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


def test_orchestrator_run_without_candidates(auth_headers) -> None:
    resp = client.post(
        "/api/v1/orchestrator/run",
        json={"team_id": "team_solo", "user_id": "user_solo", "include_candidates": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "candidate_simulation" not in payload["steps"]


def test_session_invalid_token_returns_401() -> None:
    resp = client.get("/api/v1/auth/session", headers={"Authorization": "Bearer not.a.valid.jwt"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# services.py — uncovered branches
# ---------------------------------------------------------------------------


def test_score_assessment_missing_question_defaults_zero() -> None:
    """Missing question ID → score defaults to 0.0 for that dimension."""
    scores = score_assessment({"q1": 5})  # only q1 answered
    from app.schemas import TRAIT_DIMENSIONS
    for i, dim in enumerate(TRAIT_DIMENSIONS):
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
    r = synthesis_from_compat(total_score=10.0, weak_dimensions=["chronotype_sync", "stress_response"])
    assert "friction" in r["narrative"].lower()
    assert "chronotype_sync" in r["uncertainty_note"]


def test_synthesis_from_compat_workable() -> None:
    r = synthesis_from_compat(total_score=22.0, weak_dimensions=[])
    assert "workable" in r["narrative"].lower() or "ritual" in r["narrative"].lower()


def test_compatibility_chronotype_risk_flag() -> None:
    """Very low chronotype_sync score triggers the chronotype-specific risk flag."""
    from app.schemas import TRAIT_WEIGHTS
    scores_a = {dim: w * 0.9 for dim, w in TRAIT_WEIGHTS.items()}
    scores_b = {dim: w * 0.9 for dim, w in TRAIT_WEIGHTS.items()}
    # Drive chronotype_sync scores apart to force the chronotype risk flag
    scores_a["chronotype_sync"] = TRAIT_WEIGHTS["chronotype_sync"] * 0.9
    scores_b["chronotype_sync"] = TRAIT_WEIGHTS["chronotype_sync"] * 0.05
    result = compatibility(scores_a, scores_b)
    assert any("Chronotype" in flag for flag in result["risk_flags"])


def test_mock_compatibility_incomplete_mode() -> None:
    scores = mock_compatibility_scores("test_user", data_mode="incomplete")
    none_count = sum(1 for v in scores.values() if v is None)
    assert none_count == 3


def test_assessment_questions_dimensions_match() -> None:
    """Each question should map to a valid compatibility dimension."""
    from app.schemas import TRAIT_DIMENSIONS
    questions = assessment_questions()
    assert len(questions) == 8
    dims = [q["dimension"] for q in questions]
    assert dims == TRAIT_DIMENSIONS


def test_cat_select_next_irt_semantics() -> None:
    """IRT selects by Fisher information — q2 has highest info at theta=0, not highest weight."""
    answered: dict = {}
    order = []
    for _ in range(8):
        nxt = cat_select_next_question(answered)
        if nxt is None:
            break
        order.append(nxt)
        answered[nxt] = 3
    # IRT selects q2 first (highest Fisher info at theta=0, not weight rank)
    assert order[0] == "q2"
    # No duplicates
    assert len(set(order)) == len(order)
    # Questions are drawn from the valid set
    for qid in order:
        assert qid in {f"q{i}" for i in range(1, 9)}


async def test_github_analyst_node_runs_with_members() -> None:
    """Regression: the orchestrator GitHub-analyst node uses asyncio.gather over members.

    A missing `import asyncio` in services.py raised NameError only on a live run (no test hit
    this path), surfacing as 'Orchestration failed: name asyncio is not defined'. This exercises
    the concurrent path with the deterministic (no-token, no-network) fallback.
    """
    from app.services import _github_analyst_node

    state = {
        "user_id": "user_demo",
        "member_profiles": [
            {"user_id": "user_demo", "github_handle": "octocat", "github_data": None},
            {"user_id": "user_two", "github_handle": "hubber", "github_data": None},
        ],
    }
    out = await _github_analyst_node(state)
    assert "github_signals" in out
    assert "member_github_signals" in out
    assert set(out["member_github_signals"]) == {"user_demo", "user_two"}
