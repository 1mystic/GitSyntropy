"""Reciprocal teammate recommendation engine.

GitSyntropy already scores *symmetric* pairwise compatibility (``services.compatibility``).
Symmetric scoring is not enough for a recommender: recommending B to A is only useful if B
would also accept A. This module adds **reciprocal recommendation** — the score of a match is
the *harmonic mean* of two **directional** fit scores, which punishes one-sided matches (the
standard reciprocal-recsys trick used in dating / mentorship / team-formation systems).

Two rankers are implemented and compared:

1. ``ContentRecommender`` — directional fit from trait vectors only. Needs no interaction
   history, so it handles cold-start for free (a brand-new user who has just finished the
   adaptive assessment can be ranked immediately).
2. ``MatrixFactorizationRecommender`` — latent-factor model (truncated SVD / ALS) fit on an
   observed collaboration-outcome matrix; captures preference signal beyond raw trait similarity,
   but cannot rank users unseen at fit time (falls back to the content ranker — documented
   cold-start handling).

Evaluation metrics (``ndcg_at_k``, ``hit_rate_at_k``, ``coverage``) and a synthetic-population
generator are included so the engine can be benchmarked offline with no external data.

Design notes for interviews
---------------------------
* **Why harmonic mean?** ``HM(x, y) = 2xy / (x + y)`` is dominated by the *smaller* of the two
  directional fits. A match that is great one-way but poor the other way gets a low score —
  exactly the reciprocal property. Arithmetic mean would reward a lopsided match.
* **Where does asymmetry come from?** Directional fit weights each dimension by the *seeker's*
  salience (how much that seeker emphasises the dimension), so ``fit(A→B) ≠ fit(B→A)`` even
  though the underlying trait distance is symmetric.
* **Cold-start:** assessment precedes recommendation, so every user always has a trait vector →
  the content ranker is always available, even with zero interaction history.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .schemas import TRAIT_DIMENSIONS, TRAIT_WEIGHTS, normalize_dimension_keys

_DIMS = TRAIT_DIMENSIONS
_W = np.array([TRAIT_WEIGHTS[d] for d in _DIMS], dtype=float)  # global dimension weights (1..8)
_EPS = 1e-9


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

def scores_to_vector(scores: dict[str, float | None]) -> np.ndarray:
    """Convert a (possibly legacy-keyed, possibly sparse) scores dict to a dense [0,1] vector.

    Each dimension is normalised by its max weight so all dimensions live on a common 0..1 scale.
    Missing dimensions are imputed at the neutral midpoint 0.5.
    """
    scores = normalize_dimension_keys(scores)
    vec = np.empty(len(_DIMS), dtype=float)
    for i, d in enumerate(_DIMS):
        raw = scores.get(d)
        max_w = TRAIT_WEIGHTS[d]
        vec[i] = 0.5 if raw is None else min(max(float(raw) / max_w, 0.0), 1.0)
    return vec


def _salience(seeker: np.ndarray) -> np.ndarray:
    """Per-dimension importance weights from the seeker's perspective.

    Combines the *global* dimension weight (chronotype matters more than innovation drive) with
    the seeker's own emphasis (a dimension the seeker scores strongly on is one they care about
    aligning on). Normalised to sum to 1 so directional fit stays in [0, 1].
    """
    sal = _W * (0.5 + seeker)  # 0.5 floor so a zero-score dim still carries its global weight
    return sal / (sal.sum() + _EPS)


def directional_fit(seeker: np.ndarray, candidate: np.ndarray) -> float:
    """How well *candidate* satisfies *seeker*, in [0, 1] — asymmetric.

    Per-dimension similarity ``1 - |s - c|`` weighted by the seeker's salience. Because salience
    depends on the seeker, ``directional_fit(a, b) != directional_fit(b, a)`` in general.
    """
    sim = 1.0 - np.abs(seeker - candidate)  # both already 0..1
    return float(np.dot(_salience(seeker), sim))


def reciprocal_score(a: np.ndarray, b: np.ndarray) -> float:
    """Harmonic mean of the two directional fits — the reciprocal match score in [0, 1]."""
    fa = directional_fit(a, b)
    fb = directional_fit(b, a)
    if fa <= 0 or fb <= 0:
        return 0.0
    return 2.0 * fa * fb / (fa + fb)


# ---------------------------------------------------------------------------
# Recommenders
# ---------------------------------------------------------------------------

@dataclass
class Recommendation:
    user_id: str
    score: float
    directional_to_seeker: float   # fit(candidate -> seeker): how well candidate satisfies seeker
    directional_from_seeker: float  # fit(seeker -> candidate): how well seeker satisfies candidate


class ContentRecommender:
    """Reciprocal ranking from trait vectors only (no interaction history needed)."""

    def __init__(self, profiles: dict[str, dict[str, float | None]]):
        # user_id -> dense vector
        self.vectors: dict[str, np.ndarray] = {
            uid: scores_to_vector(scores) for uid, scores in profiles.items()
        }

    def recommend(self, seeker_id: str, k: int = 5, exclude: set[str] | None = None) -> list[Recommendation]:
        if seeker_id not in self.vectors:
            raise KeyError(f"unknown seeker_id: {seeker_id}")
        exclude = (exclude or set()) | {seeker_id}
        s = self.vectors[seeker_id]
        recs: list[Recommendation] = []
        for uid, v in self.vectors.items():
            if uid in exclude:
                continue
            to_seeker = directional_fit(s, v)
            from_seeker = directional_fit(v, s)
            score = 0.0 if to_seeker <= 0 or from_seeker <= 0 else 2 * to_seeker * from_seeker / (to_seeker + from_seeker)
            recs.append(Recommendation(uid, round(score, 4), round(to_seeker, 4), round(from_seeker, 4)))
        recs.sort(key=lambda r: r.score, reverse=True)
        return recs[:k]


class MatrixFactorizationRecommender:
    """Latent-factor ranker fit on an observed collaboration-outcome matrix (truncated SVD / ALS).

    ``R[i, j]`` is the observed reciprocal-success signal between users i and j (0..1, NaN if the
    pair never collaborated). We mean-impute missing entries, mean-center, and take a rank-``f``
    truncated SVD to denoise and fill the matrix; ranking uses the reconstructed scores.

    Cold-start: a user not present at fit time has no row/column, so ``recommend`` raises and the
    caller should fall back to ``ContentRecommender`` (see ``HybridRecommender``).
    """

    def __init__(self, user_ids: list[str], interaction: np.ndarray, n_factors: int = 6):
        self.user_ids = list(user_ids)
        self.index = {uid: i for i, uid in enumerate(self.user_ids)}
        self.n_factors = min(n_factors, max(1, len(user_ids) - 1))
        self._fit(interaction)

    def _fit(self, R: np.ndarray) -> None:
        mask = ~np.isnan(R)
        global_mean = float(R[mask].mean()) if mask.any() else 0.5
        filled = np.where(mask, R, global_mean)
        self.global_mean = global_mean
        centered = filled - global_mean
        # Truncated SVD reconstruction (classic latent-factor model).
        U, S, Vt = np.linalg.svd(centered, full_matrices=False)
        f = self.n_factors
        self.recon = (U[:, :f] * S[:f]) @ Vt[:f, :] + global_mean

    def recommend(self, seeker_id: str, k: int = 5, exclude: set[str] | None = None) -> list[Recommendation]:
        if seeker_id not in self.index:
            raise KeyError(f"cold-start: {seeker_id} not in factorized population")
        exclude = (exclude or set()) | {seeker_id}
        i = self.index[seeker_id]
        row = self.recon[i]
        order = np.argsort(-row)
        recs: list[Recommendation] = []
        for j in order:
            uid = self.user_ids[j]
            if uid in exclude:
                continue
            recs.append(Recommendation(uid, round(float(row[j]), 4), float("nan"), float("nan")))
            if len(recs) >= k:
                break
        return recs


class HybridRecommender:
    """MF where possible, content-based fallback for cold-start users."""

    def __init__(self, content: ContentRecommender, mf: MatrixFactorizationRecommender | None):
        self.content = content
        self.mf = mf

    def recommend(self, seeker_id: str, k: int = 5, exclude: set[str] | None = None) -> list[Recommendation]:
        if self.mf is not None and seeker_id in self.mf.index:
            return self.mf.recommend(seeker_id, k=k, exclude=exclude)
        return self.content.recommend(seeker_id, k=k, exclude=exclude)


# ---------------------------------------------------------------------------
# Evaluation metrics
# ---------------------------------------------------------------------------

def dcg_at_k(relevances: list[float], k: int) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances[:k]))


def ndcg_at_k(ranked_ids: list[str], relevant: dict[str, float], k: int = 5) -> float:
    """NDCG@k with graded relevance (relevant maps id -> gain)."""
    gains = [relevant.get(uid, 0.0) for uid in ranked_ids[:k]]
    ideal = sorted(relevant.values(), reverse=True)
    idcg = dcg_at_k(ideal, k)
    if idcg <= 0:
        return 0.0
    return dcg_at_k(gains, k) / idcg


def hit_rate_at_k(ranked_ids: list[str], relevant: set[str], k: int = 10) -> float:
    """1.0 if any relevant item appears in the top-k, else 0.0."""
    return 1.0 if set(ranked_ids[:k]) & relevant else 0.0


def coverage(all_recommended: set[str], catalog: set[str]) -> float:
    """Fraction of the catalog that appears in at least one user's top-k list."""
    if not catalog:
        return 0.0
    return len(all_recommended & catalog) / len(catalog)


# ---------------------------------------------------------------------------
# Synthetic population + ground-truth labels (for offline benchmarking)
# ---------------------------------------------------------------------------

# Latent ground-truth model (deliberately *different* from the recommender's assumption).
# On these dimensions, real teams benefit from DIVERSITY (opposites complement): a team wants a
# mix of leaders/followers, bold/cautious, disruptive/incremental. The content recommender naively
# assumes similarity is good on every dimension, so evaluating against this latent process reveals
# where it is wrong — and where the MF ranker, learning from observed outcomes, can do better.
_DIVERSITY_DIMS = {"leadership_orientation", "risk_tolerance", "innovation_drive"}
_DIVERSITY_MASK = np.array([1.0 if d in _DIVERSITY_DIMS else 0.0 for d in _DIMS])


def generate_population(n: int, seed: int = 7) -> dict[str, dict[str, float]]:
    """Generate *n* synthetic users with weighted dimension scores (same scale as real profiles)."""
    rng = np.random.default_rng(seed)
    pop: dict[str, dict[str, float]] = {}
    for i in range(n):
        scores = {d: round(float(TRAIT_WEIGHTS[d] * rng.uniform(0.1, 1.0)), 2) for d in _DIMS}
        pop[f"synth_{i:03d}"] = scores
    return pop


# Hidden per-user "collaboration ease" (popularity) term — not visible in trait vectors, so the
# content ranker cannot see it but the MF ranker can recover it from the outcome matrix.
_popularity_cache: dict[int, np.ndarray] = {}


def _popularity(n: int, seed: int) -> np.ndarray:
    key = hash((n, seed))
    if key not in _popularity_cache:
        _popularity_cache[key] = np.random.default_rng(seed).normal(0.0, 0.12, size=n)
    return _popularity_cache[key]


def ground_truth_match_probability(
    a: np.ndarray, b: np.ndarray, rng: np.random.Generator,
    pop_a: float = 0.0, pop_b: float = 0.0,
) -> float:
    """Latent 'successful collaboration' probability — a process distinct from the recommender.

    * Similarity dimensions (chronotype, stress, work, decision, resilience): closeness is good.
    * Diversity dimensions (leadership, risk, innovation): *difference* is good (complementarity).
    * Plus a hidden popularity term per user and mild noise.

    The recommender assumes similarity-is-good everywhere, so it cannot be perfect against this —
    making NDCG/hit-rate meaningful rather than tautological.
    """
    sim_term = (1.0 - np.abs(a - b)) * (1.0 - _DIVERSITY_MASK)
    div_term = np.abs(a - b) * _DIVERSITY_MASK
    contrib = (sim_term + div_term)
    weighted = float(np.dot(_W / _W.sum(), contrib))
    latent = 0.80 * weighted + pop_a + pop_b + float(rng.normal(0, 0.04))
    return float(min(max(latent, 0.0), 1.0))


def build_interaction_matrix(
    profiles: dict[str, dict[str, float]],
    density: float = 0.4,
    seed: int = 11,
) -> tuple[list[str], np.ndarray, dict[str, dict[str, float]]]:
    """Build a partially-observed symmetric interaction matrix + the full latent labels.

    Returns ``(user_ids, R, truth)`` where ``R`` has NaN for unobserved pairs (for MF training)
    and ``truth[u][v]`` is the full latent match probability (for evaluation ground truth).
    """
    rng = np.random.default_rng(seed)
    user_ids = list(profiles)
    vecs = {uid: scores_to_vector(s) for uid, s in profiles.items()}
    n = len(user_ids)
    pop = _popularity(n, seed)  # hidden per-user collaboration-ease term
    R = np.full((n, n), np.nan, dtype=float)
    truth: dict[str, dict[str, float]] = {u: {} for u in user_ids}
    for i, ui in enumerate(user_ids):
        for j in range(i + 1, n):
            uj = user_ids[j]
            p = ground_truth_match_probability(vecs[ui], vecs[uj], rng, pop[i], pop[j])
            truth[ui][uj] = p
            truth[uj][ui] = p
            if rng.random() < density:  # only a fraction of pairs are observed
                R[i, j] = p
                R[j, i] = p
    return user_ids, R, truth
