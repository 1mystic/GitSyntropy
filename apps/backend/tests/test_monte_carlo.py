"""Tests for Feature 8: Monte Carlo candidate simulation (1 000 iterations)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ASHTAKOOT_DIMENSIONS, ASHTAKOOT_WEIGHTS
from app.services import monte_carlo_candidate_simulation

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests — monte_carlo_candidate_simulation
# ---------------------------------------------------------------------------


def _neutral_team() -> list[dict]:
    return [{dim: round(w * 0.5, 2) for dim, w in ASHTAKOOT_WEIGHTS.items()}]


def _weak_team() -> list[dict]:
    """Team weak in high-weight dimensions."""
    return [{
        dim: round(w * 0.2, 2) if w >= 5 else round(w * 0.7, 2)
        for dim, w in ASHTAKOOT_WEIGHTS.items()
    }]


def test_simulation_returns_required_keys() -> None:
    result = monte_carlo_candidate_simulation(_neutral_team(), n_iterations=200)
    required = {
        "n_iterations", "optimal_profile", "mean_improvement",
        "best_improvement", "p25_improvement", "p75_improvement",
        "weak_dimensions_targeted", "confidence", "status",
    }
    assert required <= result.keys()


def test_simulation_n_iterations_matches() -> None:
    result = monte_carlo_candidate_simulation(_neutral_team(), n_iterations=500)
    assert result["n_iterations"] == 500


def test_simulation_optimal_profile_has_all_dimensions() -> None:
    result = monte_carlo_candidate_simulation(_neutral_team(), n_iterations=200)
    assert set(result["optimal_profile"].keys()) == set(ASHTAKOOT_DIMENSIONS)


def test_simulation_optimal_scores_in_valid_range() -> None:
    result = monte_carlo_candidate_simulation(_neutral_team(), n_iterations=200)
    for dim, score in result["optimal_profile"].items():
        max_w = ASHTAKOOT_WEIGHTS[dim]
        assert 0 <= score <= max_w, f"{dim} score {score} out of range 0–{max_w}"


def test_simulation_confidence_is_one_at_1000() -> None:
    result = monte_carlo_candidate_simulation(_neutral_team(), n_iterations=1000)
    assert result["confidence"] == 1.0


def test_simulation_targets_weak_dimensions() -> None:
    result = monte_carlo_candidate_simulation(_weak_team(), n_iterations=300)
    assert len(result["weak_dimensions_targeted"]) > 0
    # Weak dims should be the high-weight ones (≥5 pts) that were set to 20 %
    for dim in result["weak_dimensions_targeted"]:
        assert ASHTAKOOT_WEIGHTS[dim] >= 5


def test_simulation_empty_team_uses_neutral_baseline() -> None:
    result = monte_carlo_candidate_simulation([], n_iterations=200)
    assert result["status"] == "complete"
    assert result["optimal_profile"]


def test_simulation_percentile_ordering() -> None:
    result = monte_carlo_candidate_simulation(_neutral_team(), n_iterations=500)
    assert result["p25_improvement"] <= result["mean_improvement"]
    assert result["mean_improvement"] <= result["p75_improvement"] + 0.5  # allow rounding


def test_simulation_deterministic() -> None:
    """Same inputs → same optimal profile (seed=42)."""
    r1 = monte_carlo_candidate_simulation(_neutral_team(), n_iterations=300)
    r2 = monte_carlo_candidate_simulation(_neutral_team(), n_iterations=300)
    assert r1["optimal_profile"] == r2["optimal_profile"]


# ---------------------------------------------------------------------------
# Integration tests — POST /candidates/simulate
# ---------------------------------------------------------------------------


def test_simulate_endpoint_default_iterations() -> None:
    resp = client.post(
        "/api/v1/candidates/simulate",
        json={"team_scores": [], "n_iterations": 1000},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["n_iterations"] == 1000
    assert payload["confidence"] == 1.0
    assert payload["status"] == "complete"
    assert set(payload["optimal_profile"].keys()) == set(ASHTAKOOT_DIMENSIONS)


def test_simulate_endpoint_with_team_scores() -> None:
    team = [{dim: round(w * 0.6, 2) for dim, w in ASHTAKOOT_WEIGHTS.items()}]
    resp = client.post(
        "/api/v1/candidates/simulate",
        json={"team_scores": team, "n_iterations": 200},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["n_iterations"] == 200
    assert "optimal_profile" in payload


def test_simulate_endpoint_rejects_zero_iterations() -> None:
    resp = client.post(
        "/api/v1/candidates/simulate",
        json={"team_scores": [], "n_iterations": 50},  # below min 100
    )
    assert resp.status_code == 422


def test_simulate_endpoint_rejects_excess_iterations() -> None:
    resp = client.post(
        "/api/v1/candidates/simulate",
        json={"team_scores": [], "n_iterations": 9999},  # above max 5000
    )
    assert resp.status_code == 422
