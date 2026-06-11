"""Offline benchmark for the reciprocal recommender.

Generates a synthetic user population, builds a partially-observed collaboration matrix, then
compares the content-based reciprocal ranker against the matrix-factorization ranker on:

  * NDCG@5      — ranking quality against graded latent match probabilities
  * Hit-rate@10 — did a truly-good partner make the top-10?
  * Coverage    — fraction of the catalog ever recommended (diversity / popularity-bias check)

Run:  uv run python scripts/eval_recommender.py
Writes a short markdown summary to docs/recommender_eval.md and prints the table.

No external data or services required — everything is synthetic and deterministic per seed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `app` importable when run from the backend dir or repo root.
THIS = Path(__file__).resolve()
BACKEND = THIS.parents[1] / "apps" / "backend"
if (BACKEND / "app").exists():
    sys.path.insert(0, str(BACKEND))

import numpy as np  # noqa: E402

from app.recommender import (  # noqa: E402
    ContentRecommender,
    MatrixFactorizationRecommender,
    build_interaction_matrix,
    coverage,
    generate_population,
    hit_rate_at_k,
    ndcg_at_k,
)

N_USERS = 200
DENSITY = 0.4          # fraction of pairs observed in the training matrix
N_FACTORS = 8
K_NDCG = 5
K_HIT = 10
REL_THRESHOLD = 0.75   # a pair is "truly relevant" if latent match prob >= this


def evaluate(recommender, user_ids, truth, k_ndcg=K_NDCG, k_hit=K_HIT) -> dict[str, float]:
    ndcgs, hits = [], []
    recommended: set[str] = set()
    for uid in user_ids:
        try:
            recs = recommender.recommend(uid, k=max(k_ndcg, k_hit))
        except KeyError:
            continue
        ranked = [r.user_id for r in recs]
        recommended.update(ranked[:k_hit])
        graded = {v: g for v, g in truth[uid].items()}             # graded relevance
        relevant = {v for v, g in truth[uid].items() if g >= REL_THRESHOLD}
        ndcgs.append(ndcg_at_k(ranked, graded, k=k_ndcg))
        if relevant:
            hits.append(hit_rate_at_k(ranked, relevant, k=k_hit))
    return {
        "ndcg@%d" % k_ndcg: float(np.mean(ndcgs)) if ndcgs else 0.0,
        "hit_rate@%d" % k_hit: float(np.mean(hits)) if hits else 0.0,
        "coverage": coverage(recommended, set(user_ids)),
    }


def main() -> None:
    pop = generate_population(N_USERS, seed=7)
    user_ids, R, truth = build_interaction_matrix(pop, density=DENSITY, seed=11)

    content = ContentRecommender(pop)
    mf = MatrixFactorizationRecommender(user_ids, R, n_factors=N_FACTORS)

    content_metrics = evaluate(content, user_ids, truth)
    mf_metrics = evaluate(mf, user_ids, truth)

    header = f"{'metric':<14}{'content':>12}{'matrix-fact':>14}"
    rows = [header, "-" * len(header)]
    for key in content_metrics:
        rows.append(f"{key:<14}{content_metrics[key]:>12.4f}{mf_metrics[key]:>14.4f}")
    table = "\n".join(rows)
    print(table)

    out = THIS.parents[1] / "docs" / "recommender_eval.md"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Reciprocal Recommender — Offline Evaluation\n\n")
        fh.write(
            f"Synthetic population: **{N_USERS} users**, observed-pair density **{DENSITY}**, "
            f"MF latent factors **{N_FACTORS}**, relevance threshold **{REL_THRESHOLD}**. "
            "Deterministic per seed; reproduce with `uv run python scripts/eval_recommender.py`.\n\n"
        )
        fh.write("| metric | content-based | matrix-factorization |\n|---|---|---|\n")
        for key in content_metrics:
            fh.write(f"| {key} | {content_metrics[key]:.4f} | {mf_metrics[key]:.4f} |\n")
        fh.write(
            "\n**Reading the result:** the content ranker recovers the reciprocal structure "
            "directly from trait vectors and needs no history (cold-start safe). The MF ranker "
            "learns from the observed collaboration matrix and improves where interaction signal "
            "exists, but cannot rank users unseen at fit time (cold-start → content fallback via "
            "`HybridRecommender`).\n"
        )
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
