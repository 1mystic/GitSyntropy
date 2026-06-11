"""Tests for the reciprocal recommendation engine."""

import numpy as np
import pytest

from app.recommender import (
    ContentRecommender,
    HybridRecommender,
    MatrixFactorizationRecommender,
    build_interaction_matrix,
    coverage,
    directional_fit,
    generate_population,
    hit_rate_at_k,
    ndcg_at_k,
    reciprocal_score,
    scores_to_vector,
)
from app.schemas import TRAIT_DIMENSIONS, TRAIT_WEIGHTS


def _vec(val: float) -> np.ndarray:
    return np.full(len(TRAIT_DIMENSIONS), val, dtype=float)


def test_scores_to_vector_normalizes_and_imputes() -> None:
    scores = {d: TRAIT_WEIGHTS[d] for d in TRAIT_DIMENSIONS}  # all at max
    v = scores_to_vector(scores)
    assert np.allclose(v, 1.0)
    # missing dim imputed at 0.5
    partial = {TRAIT_DIMENSIONS[0]: TRAIT_WEIGHTS[TRAIT_DIMENSIONS[0]]}
    vp = scores_to_vector(partial)
    assert vp[0] == pytest.approx(1.0)
    assert vp[1] == pytest.approx(0.5)


def test_scores_to_vector_accepts_legacy_keys() -> None:
    # read-shim path: legacy key should map and not crash
    v = scores_to_vector({"nadi_chronotype_sync": 8.0})
    idx = TRAIT_DIMENSIONS.index("chronotype_sync")
    assert v[idx] == pytest.approx(1.0)


def test_directional_fit_is_asymmetric() -> None:
    # Per-dimension differences must vary so salience weighting (which differs by seeker) matters.
    a = np.array([0.9, 0.8, 0.2, 0.5, 0.9, 0.1, 0.6, 0.3])
    b = np.array([0.4, 0.8, 0.9, 0.5, 0.2, 0.1, 0.1, 0.9])
    assert directional_fit(a, b) != pytest.approx(directional_fit(b, a))


def test_reciprocal_punishes_one_sided_match() -> None:
    a = _vec(0.9)
    identical = _vec(0.9)
    opposite = _vec(0.1)
    assert reciprocal_score(a, identical) > reciprocal_score(a, opposite)
    # harmonic mean <= min directional fit's arithmetic counterpart: never exceeds 1
    assert 0.0 <= reciprocal_score(a, opposite) <= 1.0


def test_content_recommender_ranks_and_excludes_self() -> None:
    pop = generate_population(30, seed=3)
    rec = ContentRecommender(pop)
    seeker = next(iter(pop))
    out = rec.recommend(seeker, k=5)
    assert len(out) == 5
    assert seeker not in {r.user_id for r in out}
    scores = [r.score for r in out]
    assert scores == sorted(scores, reverse=True)  # descending


def test_mf_cold_start_falls_back_to_content() -> None:
    pop = generate_population(40, seed=4)
    user_ids, R, _ = build_interaction_matrix(pop, density=0.4, seed=5)
    mf = MatrixFactorizationRecommender(user_ids, R, n_factors=6)
    content = ContentRecommender(pop)
    hybrid = HybridRecommender(content, mf)

    # known user -> MF path
    assert hybrid.recommend(user_ids[0], k=5)
    # unknown user -> content fallback (no exception)
    pop["cold_new"] = {d: TRAIT_WEIGHTS[d] * 0.5 for d in TRAIT_DIMENSIONS}
    hybrid_cs = HybridRecommender(ContentRecommender(pop), mf)
    out = hybrid_cs.recommend("cold_new", k=5)
    assert len(out) == 5
    with pytest.raises(KeyError):
        mf.recommend("cold_new")


def test_ndcg_perfect_ordering_is_one() -> None:
    relevant = {"a": 1.0, "b": 0.5, "c": 0.2}
    assert ndcg_at_k(["a", "b", "c"], relevant, k=3) == pytest.approx(1.0)
    # worst ordering scores lower
    assert ndcg_at_k(["c", "b", "a"], relevant, k=3) < 1.0


def test_metrics_basic() -> None:
    assert hit_rate_at_k(["x", "y", "z"], {"y"}, k=3) == 1.0
    assert hit_rate_at_k(["x", "y", "z"], {"w"}, k=3) == 0.0
    assert coverage({"a", "b"}, {"a", "b", "c", "d"}) == pytest.approx(0.5)
