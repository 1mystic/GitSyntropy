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

---

## WS-3a — Calibration evidence (done 2026-06-11)

**What:** `scripts/calibration_evidence.py` now emits `docs/calibration_reliability.png` plus
`docs/calibration_evidence.md` for the Platt-scaled compatibility-confidence model.

**Measured result:** on 8,000 held-out synthetic samples, naive coverage confidence had
ECE **0.3748**; Platt-scaled confidence had ECE **0.0099**. That is a **97% reduction**.

**Interview talking point:** the calibration layer is not decorative. It converts a brittle
signal-coverage proxy into a probabilistic confidence score with a reliability diagram that sits
close to the diagonal.

---

## WS-3b — CAT ablation + ICC plot (done 2026-06-11)

**What:** `scripts/cat_ablation.py` now emits `docs/cat_ablation.png`, `docs/cat_ablation.md`,
`docs/irt_icc.png`, and `docs/irt_icc.md`. It compares adaptive Fisher-information selection to
fixed-order administration on the real 8-item 3PL bank and also renders the item characteristic
curves.

**Measured result (corrected):** over 600 simulated examinees (θ ~ N(0,1)), adaptive selection
reaches **SE ≤ 0.90 in 2.0 items vs 3.0 for fixed order** (4% more precise at item 2). The two
policies **converge by item ~4** — an 8-item bank has few high-information items, so once they are
administered, order stops mattering. **Actionable finding:** EAP SE **floors at ≈0.64**, never
reaching the deployed `_STOP_SE = 0.35`, so the live CAT always administers all 8 — the fix is a
larger item bank, where Fisher-info savings grow. (An earlier run used target SE 0.80, which sits
inside the converged zone and produced a meaningless 4.22 vs 4.23; corrected to 0.90.)

**Interview talking point:** the ICC plot makes the 3PL story visual: low-difficulty items are
useful near the prior mean, while the hardest item is almost uninformative at start-up. Fisher
selection encodes that directly.

---

## WS-4 — Agent trace view + hire-sim UI (done 2026-06-11)

**What:** the orchestrator now persists per-node trace snapshots on `agent_runs.agent_events`, with
duration timing captured from the websocket/LangGraph step stream. New read-only admin endpoint:
`GET /api/v1/admin/agent-runs`. The superadmin dashboard now renders those traces as a read-only
step-by-step view.

**Also shipped:** the dashboard now exposes the Monte Carlo hire simulation as a real UI card. It
uses the current compatibility vector as the seed profile and calls `/candidates/simulate` so the
"optimal profile / expected improvement / weak dimensions targeted" story is visible in the app.

**Prod schema:** added `apps/backend/migrations/0002_agent_events.sql` (idempotent
`ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS agent_events JSONB`) — required because
`CREATE TABLE IF NOT EXISTS` will not add the column to an existing prod `agent_runs` table.

**Validation:** the `no such table: teams` failure flagged here was a **test-harness regression**
(not in the WS-4 code) and has been fixed — see the "Test-harness fix" section below. Full suite is
now **92 passed**; frontend `astro check` **0 errors**.

---

## WS-5 — Known issues cleanup (done 2026-06-11)

**F3 fixed:** `github_client.py` no longer limits collaboration scanning to owner repos. The
orchestrator GitHub analyst now enriches every team member's GitHub profile, not just the primary
user, while preserving the primary signal shape for synthesis.

**F5 fixed:** report persistence is now backed by `team_scores` in Postgres. The websocket save
path returns the real report id, the dashboard/report pages fetch persisted reports from the API,
and localStorage is now only a cache fallback.

**O4 fixed:** the synthesis fallback is no longer a static template. `synthesis_from_compat()` now
derives recommendations from the weak dimensions / risk flags instead of returning generic advice.

**Interview talking point:** this closes the "looks polished but is mostly local state" gap. The
report history, trace view, and hire simulation are all now grounded in persisted backend data.

---

## Test-harness fix (regression surfaced by parallel work; fixed 2026-06-11)

Full `pytest` had started failing (`test_teams.py`: `no such table: teams`) — an aiosqlite +
StaticPool + per-test-event-loop fragility surfaced once async tests were added. Fixed in
`tests/conftest.py`: switched the test DB to a **named shared-cache** in-memory SQLite
(`cache=shared`) plus a process-lifetime keepalive `sqlite3` connection that pins the DB across loops.
Suite is now **order-independent**. **92 passed; frontend `astro check` 0 errors.**

## Pending user actions (GitSyntropy)
1. `git add -A && git commit -m "GitSyntropy WS-1..5 upgrades + test-harness fix"`
2. Run on Supabase (query editor): `apps/backend/migrations/0001_rename_dimensions.sql` then
   `apps/backend/migrations/0002_agent_events.sql`. (Both idempotent; the read-shim and
   `CREATE TABLE IF NOT EXISTS` keep things working pre-migration, but apply them to be correct.)

## Local demo tooling + UI gap fix (2026-06-11)

- **`scripts/seed_demo.py`** (local-only; hard SQLite guard, `seed_demo_` prefix, `--clear`): now
  seeds 10 assessed users **and** a "Demo Squad (seed)" team (owner + 5 members) **and** a real
  compatibility report, so the dashboard/compatibility/insights/hire-sim all populate locally — not
  just the recommendation pool. `--clear` removes only seeded rows + the seed team (real teams kept).
- **Recommendations UI was unmounted** (gap from WS-2 / parallel work): `RecommendationsClient` existed
  but no page rendered it. Now reads `$activeTeam` and is mounted on `compatibility.astro`.
- **API base hardened** (`src/lib/api.ts`): `PUBLIC_API_BASE` env wins (vercel.json sets the Render URL
  on deploy); else host-based auto-detect → localhost when on localhost/127.0.0.1, else
  `https://gitsyntropy.onrender.com`. Same logic for the WS base. Local always hits localhost; a
  deployed build can never accidentally call localhost. `astro check` 0 errors.

## Deployment-readiness fixes (2026-06-11)

- **CRITICAL — `asyncio` NameError**: `services.py` used `asyncio.gather` in `_github_analyst_node`
  (WS-5 F3 concurrent GitHub analysis) but never imported `asyncio` → every "Run Analysis" failed
  with "Orchestration failed: name 'asyncio' is not defined" (local AND prod). Added `import asyncio`.
  Added regression test `test_github_analyst_node_runs_with_members` (the live orchestrator path had
  no test coverage, which is why CI missed it). **93 tests pass.**
- **Hydration errors**: `NavUser` + `GlobalTeamSelector` are session/localStorage-driven and were
  SSR'd via `client:load`, causing "Hydration failed" cascades. Switched to `client:only="react"` in
  `SideNav.astro` — no server HTML to mismatch. `astro check` 0 errors.
- **API/WS base auto-detection** (recap): env var (vercel.json → Render) wins; else host-based
  (localhost → local, else Render). Local always local; deployed always Render.
- **Prod safety:** `matplotlib` is a **dev/script** dependency only (not imported by `app/`), so the
  Render production install does not pull it. Local SQLite demo DB is gitignored.
- **Known minor (pre-existing, non-blocking):** React duplicate-key `` warning in `CompatibilityClient`
  option lists — cosmetic, does not affect correctness.

### Deploy checklist
1. Commit + push (Render auto-deploys backend; Vercel auto-deploys frontend with vercel.json env).
2. Apply on Supabase (query editor), in order: `apps/backend/migrations/0001_rename_dimensions.sql`,
   then `0002_agent_events.sql`. Both idempotent. Required for correct real data (renamed keys +
   agent_events column).
3. Verify deployed: frontend (Vercel) → `gitsyntropy.onrender.com` → Supabase; run an assessment +
   "Run Analysis" to confirm the agent trace persists.
