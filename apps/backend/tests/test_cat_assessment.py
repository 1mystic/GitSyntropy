"""Tests for Feature 8: CAT (Computerized Adaptive Testing) assessment."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import (
    ASHTAKOOT_DIMENSIONS,
    cat_select_next_question,
    cat_rationale,
    cat_estimated_remaining,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests — cat_select_next_question
# ---------------------------------------------------------------------------


def test_cat_first_question_is_highest_weight() -> None:
    """With no answers, the first question should be q8 (nadi = 8 pts)."""
    nxt = cat_select_next_question({})
    assert nxt == "q8"


def test_cat_returns_none_when_all_answered() -> None:
    all_answers = {f"q{i + 1}": 3 for i in range(len(ASHTAKOOT_DIMENSIONS))}
    assert cat_select_next_question(all_answers) is None


def test_cat_skips_answered_questions() -> None:
    answered = {"q8": 4, "q7": 2}
    nxt = cat_select_next_question(answered)
    assert nxt not in answered
    assert nxt == "q6"  # next highest weight after q7 & q8


def test_cat_early_stop_when_high_weight_covered() -> None:
    """If high-weight (≥4) questions are all answered and ≥70 % weight covered, stop."""
    # q8(8)+q7(7)+q6(6)+q5(5)+q4(4) = 30/36 = 83 % — all ≥4-weight done
    answered = {"q8": 3, "q7": 3, "q6": 3, "q5": 3, "q4": 3}
    nxt = cat_select_next_question(answered)
    assert nxt is None  # early stop triggered


def test_cat_does_not_stop_early_with_few_answers() -> None:
    answered = {"q8": 3}
    nxt = cat_select_next_question(answered)
    assert nxt is not None


def test_cat_rationale_first_question() -> None:
    r = cat_rationale("q8", {})
    assert "q8" in r
    assert "highest" in r.lower()


def test_cat_rationale_completion() -> None:
    r = cat_rationale(None, {"q8": 3})
    assert "complete" in r.lower()


def test_cat_estimated_remaining_full() -> None:
    assert cat_estimated_remaining("q8", {}) == 8


def test_cat_estimated_remaining_partial() -> None:
    assert cat_estimated_remaining("q7", {"q8": 3}) == 7


def test_cat_estimated_remaining_done() -> None:
    assert cat_estimated_remaining(None, {"q8": 3}) == 0


# ---------------------------------------------------------------------------
# Integration tests — POST /assessment/cat/next
# ---------------------------------------------------------------------------


def test_cat_next_endpoint_empty_answers() -> None:
    resp = client.post("/api/v1/assessment/cat/next", json={"current_answers": {}})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["next_question_id"] == "q8"
    assert payload["question"] is not None
    assert payload["question"]["id"] == "q8"
    assert payload["can_stop_early"] is False
    assert payload["estimated_remaining"] == 8


def test_cat_next_endpoint_partial_answers() -> None:
    resp = client.post(
        "/api/v1/assessment/cat/next",
        json={"current_answers": {"q8": 4, "q7": 2}},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["next_question_id"] == "q6"
    assert payload["can_stop_early"] is False


def test_cat_next_endpoint_all_answered() -> None:
    all_answers = {f"q{i + 1}": 3 for i in range(len(ASHTAKOOT_DIMENSIONS))}
    resp = client.post("/api/v1/assessment/cat/next", json={"current_answers": all_answers})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["next_question_id"] is None
    assert payload["can_stop_early"] is True
    assert payload["estimated_remaining"] == 0


def test_cat_next_endpoint_early_stop() -> None:
    """High-weight questions done → endpoint signals early stop."""
    answers = {"q8": 3, "q7": 3, "q6": 3, "q5": 3, "q4": 3}
    resp = client.post("/api/v1/assessment/cat/next", json={"current_answers": answers})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["can_stop_early"] is True


def test_cat_next_rejects_out_of_range_answer() -> None:
    resp = client.post(
        "/api/v1/assessment/cat/next",
        json={"current_answers": {"q8": 6}},  # 6 > max 5
    )
    assert resp.status_code == 422
