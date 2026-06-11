# Reciprocal Recommender — Offline Evaluation

Synthetic population: **200 users**, observed-pair density **0.4**, MF latent factors **8**, relevance threshold **0.75**. Deterministic per seed; reproduce with `uv run python scripts/eval_recommender.py`.

| metric | content-based | matrix-factorization |
|---|---|---|
| ndcg@5 | 0.7112 | 0.9002 |
| hit_rate@10 | 0.6181 | 0.9583 |
| coverage | 1.0000 | 0.3750 |

**Reading the result:** the content ranker recovers the reciprocal structure directly from trait vectors and needs no history (cold-start safe). The MF ranker learns from the observed collaboration matrix and improves where interaction signal exists, but cannot rank users unseen at fit time (cold-start → content fallback via `HybridRecommender`).
