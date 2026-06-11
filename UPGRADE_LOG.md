# GitSyntropy — Upgrade Log

Running record of upgrade decisions, measured metrics, and interview talking points.
Folded into `INTERVIEW_PREP.md` at the end of the upgrade cycle.

---

## WS-1 — Neutral dimension naming (done 2026-06-11)

**What changed:** The 8 compatibility dimensions were internally named after the Vedic
Ashtakoot (kundali marriage-matching) koots. All code, tests, scripts, Claude prompts, and
interview-facing docs were refactored to neutral psychometric slugs:

| legacy key | new key |
|---|---|
| varna_alignment | innovation_drive |
| vashya_influence | leadership_orientation |
| tara_resilience | team_resilience |
| yoni_workstyle | work_style |
| graha_maitri_cognition | decision_style |
| gana_temperament | risk_tolerance |
| bhakoot_strategy | stress_response |
| nadi_chronotype_sync | chronotype_sync |

**Why:** removes an interview liability — a reviewer reading the code could otherwise dismiss
the (genuinely rigorous) IRT/Platt math as astrology. The 8-dimension *weighted* structure is
kept and reframed honestly as a multi-criteria weighted psychometric model; the 1–8 weights are
stated as a **design hypothesis**, not an empirically-fitted factor loading.

**Backward compatibility:**
- `schemas.py`: `ASHTAKOOT_DIMENSIONS/ASHTAKOOT_WEIGHTS` → `TRAIT_DIMENSIONS/TRAIT_WEIGHTS`;
  added `LEGACY_DIMENSION_MAP` + `normalize_dimension_keys()` read-time shim.
- Shim applied at all 3 DB-read boundaries in `services.py` (`get_assessment_response`,
  `_load_member_profiles`, `get_real_scores_for_user`) so legacy stored JSON never breaks.
- One-time migration: `apps/backend/migrations/0001_rename_dimensions.sql` (text-replace over
  JSONB; remaps `psychometric_profiles.scores` and `team_scores.dimension_scores/weak/strong`).
  Apply on a Supabase branch, verify, promote; then the shim can be removed.

**Verification:** `uv run python -m pytest -q` → **83 passed**. All changed Python compiles.

**Not touched (deliberate):** `docs/RESEARCH_PAPER_PLAN.md`, `paper/*.tex`, `scripts/plan1.md`,
`scripts/reprot1.md` keep the Ashtakoot framing — it is an intentional, disclosed academic
choice (MCDM precursor) and is the author's call to change. `Claude-prompt-guides/*` is historical
build scaffolding, left as-is.

**Interview talking point:** *"Team fit is multi-dimensional, so I modelled it as eight
orthogonal psychometric dimensions, integer-weighted 1–8 by impact on cohesion (36-pt scale).
The weighting is a stated design hypothesis; the calibration layer quantifies trust in each score."*

**Resume-safe one-liner:** weighted multi-criteria psychometric compatibility model with
IRT-scored dimensions and Platt-calibrated confidence.

---

## WS-2 — Reciprocal recommendation engine (done 2026-06-11)

**What:** new `apps/backend/app/recommender.py` — reciprocal teammate recommender. Match score =
**harmonic mean** of two **directional** fit scores (how well a candidate satisfies the seeker AND
vice-versa), so one-sided matches are penalised. Asymmetry comes from per-seeker dimension
*salience*. Two rankers implemented and compared:
- `ContentRecommender` — directional fit from trait vectors only; **cold-start safe** (assessment
  precedes recommendation, so a brand-new user is always rankable).
- `MatrixFactorizationRecommender` — truncated-SVD latent-factor model on an observed
  collaboration-outcome matrix; `HybridRecommender` falls back to content for unseen users.

**Honest eval (`scripts/eval_recommender.py` → `docs/recommender_eval.md`):** the synthetic
ground-truth process is deliberately **different** from the recommender's assumption — some
dimensions reward *diversity* (leadership/risk/innovation) not similarity, plus a hidden per-user
popularity term. So the benchmark is non-tautological. Measured on 200 synthetic users, 0.4
observed-pair density:

| metric | content | matrix-fact |
|---|---|---|
| NDCG@5 | 0.71 | 0.90 |
| hit-rate@10 | 0.62 | 0.96 |
| coverage | 1.00 | 0.375 |

**Interview narrative:** MF wins accuracy (learns the diversity + hidden-popularity signal content
can't see) but shows classic **popularity bias** (low coverage); content is less accurate but fully
diverse and cold-start safe → that accuracy/coverage tradeoff + cold-start fallback is the story.

**Production wiring:** `GET /teams/{id}/recommendations?seeker_id=&k=` (30/min limit) →
`services.recommend_teammates` (candidate pool = all assessed users minus current members). Prod
uses the cold-start-safe content ranker until real collaboration outcomes accumulate (stated
honestly). Frontend: `api.teamRecommendations` + `RecommendationsClient.tsx`.

**Verification:** backend `91 passed` (was 83; +8 recommender tests). Frontend `astro check` →
**0 errors** (also fixed a pre-existing `listTeams` arg bug in `GlobalTeamSelector.tsx`).

**Resume line:** "Built and benchmarked a reciprocal teammate recommender (content-based vs
matrix-factorization), NDCG@5 0.90, with documented cold-start handling and an honest
accuracy-vs-coverage analysis."
