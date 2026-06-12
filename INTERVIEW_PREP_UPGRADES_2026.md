# GitSyntropy — 2026 Upgrade Deep-Dive (Companion to INTERVIEW_PREP.md)

Read `INTERVIEW_PREP.md` first (the base engine: IRT-3PL/CAT, Platt calibration, Monte Carlo,
LangGraph, security, DB, frontend). This companion covers everything added in the 2026 upgrade and
is the part most worth rehearsing — it is where the **measured numbers** and **engineering-judgment
stories** live.

---

## 1. Reciprocal Recommendation Engine (`app/recommender.py`)

**Problem.** The base engine scores *symmetric* pairwise compatibility. A recommender needs more:
recommending B to A is useless if B is a poor match for A. This is the **reciprocal recommendation**
problem (dating / mentorship / team-formation literature).

**Design.**
- Match score = **harmonic mean of two *directional* fit scores**:
  `HM(fit(A->B), fit(B->A)) = 2xy/(x+y)`. The harmonic mean is dominated by the smaller term, so a
  one-sided match scores low — exactly the reciprocal property. (Arithmetic mean would reward it.)
- Asymmetry source: `directional_fit(seeker, candidate)` weights each dimension by the **seeker's
  salience** (global weight x the seeker's own emphasis), so `fit(A->B) != fit(B->A)`.
- Two rankers, compared:
  - **ContentRecommender** — directional fit from trait vectors only. **Cold-start safe**: the
    adaptive assessment always runs *before* recommendation, so a brand-new user is rankable with
    zero interaction history.
  - **MatrixFactorizationRecommender** — truncated-SVD latent-factor model over an observed
    collaboration-outcome matrix. `HybridRecommender` uses MF where possible, content fallback for
    users unseen at fit time.

**Measured (non-tautological) — `scripts/eval_recommender.py` -> `docs/recommender_eval.md`.**
The synthetic ground truth is deliberately *different* from the recommender's assumption: some
dimensions reward **diversity** (leadership / risk / innovation — opposites complement) not
similarity, plus a hidden per-user popularity term. 200 users, 0.4 observed-pair density:

| metric | content-based | matrix-factorization |
|---|---|---|
| NDCG@5 | 0.71 | **0.90** |
| hit-rate@10 | 0.62 | 0.96 |
| coverage | **1.00** | 0.375 |

**The story:** MF wins accuracy because it learns the diversity + hidden-popularity signal the
content model can't see — but shows classic **popularity bias** (coverage 0.375). Content is less
accurate but fully diverse and cold-start safe. That accuracy-vs-coverage tradeoff plus the
cold-start fallback is the senior answer.

**Production wiring.** `GET /teams/{id}/recommendations?seeker_id=&k=` ->
`services.recommend_teammates` (pool = all assessed users minus current members). Production uses the
cold-start-safe content ranker until enough real outcomes accumulate to fit MF — stated honestly.
*Note:* candidates with no GitHub identity show `github_handle: null`; the UI falls back to user_id.

**Likely Qs.**
- *Why harmonic, not arithmetic, mean?* punishes one-sided matches; dominated by the min.
- *Where does asymmetry come from if trait distance is symmetric?* per-seeker salience.
- *Brand-new user?* assessment precedes recommendation -> content ranker always works; MF falls back.
- *MF NDCG is higher, why not always use it?* coverage 0.375 = popularity bias; cold-start; needs
  real outcome data. A tradeoff, not a free win.

---

## 2. Calibration Evidence (`scripts/calibration_evidence.py`)

The base doc *claimed* Platt calibration; this proves it. 8,000-sample held-out set, same latent
process as the fit (different seed):

| confidence source | Expected Calibration Error (ECE) |
|---|---|
| Naive (signal coverage) | 0.3748 |
| **Platt-scaled** | **0.0099** |

**97% ECE reduction.** Artifact: `docs/calibration_reliability.png` (Platt curve hugs the diagonal,
naive curve departs). **Story:** the calibration layer is not decorative — it converts a brittle
coverage proxy into a probability that means what it says (says 70% -> right ~70% of the time). A
reliability diagram in a repo is rare and signals you understand calibration.

---

## 3. CAT Ablation + ICC (`scripts/cat_ablation.py`)

Adaptive (Fisher-information) vs fixed-order item selection on the **real 8-item 3PL bank**, 600
simulated examinees:

- Adaptive reaches **SE <= 0.90 in 2.0 items vs 3.0 for fixed** (~4% more precise at item 2).
- **Honest finding (say this unprompted):** the policies **converge by item ~4** — an 8-item bank
  has too few high-information items for ordering to matter long. And EAP SE **floors at ~0.64**, so
  it never reaches the deployed `_STOP_SE = 0.35`: the live CAT currently always administers all 8.
  The fix is a **larger item bank**, where Fisher-information savings grow. Knowing the limitation of
  your own system is the signal — not a fake "8 vs 20" headline.
- ICC: `docs/irt_icc.png` plots the eight 3PL curves — low-difficulty items are informative near the
  prior mean; the hardest item is near-useless at start-up, which is why CAT picks q2/q3 first.

---

## 4. Agent Observability — persisted trace (`agent_runs.agent_events`)

The WebSocket orchestrator (`main.py`) persists per-node trace events (step, status, `duration_ms`,
timestamp) to `agent_runs.agent_events` via `services.persist_agent_run_trace`, exposed read-only
through superadmin-guarded `GET /api/v1/admin/agent-runs` and rendered as the **Agent Trace View**
(Admin Panel, bottom, full-width). This is the concrete answer to *"what does LangGraph buy you over
a function pipeline?"* — per-node isolation, timing, status, replayable audit trail. Migration
`0002_agent_events.sql` adds the column to existing prod tables.

*Known edge case (be honest if asked):* on Supabase's pooled connection, mid-stream trace writes on
the shared request session can occasionally land only the first event (the run still completes and
saves its report; the live dashboard stream is unaffected). Robust fix: persist the trace on a
dedicated short-lived DB session rather than the shared request session.

---

## 5. Naming Decision — neutral psychometric model

The 8 dimensions were refactored from Vedic-Ashtakoot-derived keys to neutral slugs
(`innovation_drive` ... `chronotype_sync`) across code, tests, prompts, and interview docs, with a
read-time shim (`normalize_dimension_keys`) + migration `0001` preserving stored data. **Why it
matters:** a reviewer reading astrology-derived identifiers could dismiss the genuine IRT/Platt rigor
as pseudoscience. The model is framed honestly as a **multi-criteria weighted psychometric model**
whose 1-8 weights are a **stated design hypothesis**, not an empirically-fitted factor loading; the
calibration layer quantifies trust in each score.

---

## 6. Engineering-maturity stories ("tell me about a bug you fixed")

- **`asyncio` NameError in the orchestrator** — the concurrent GitHub-analysis node called
  `asyncio.gather` without importing `asyncio`; it failed only on a *live* run (no test covered that
  path) as "Orchestration failed: name 'asyncio' is not defined". Fix + a regression test exercising
  the node. Lesson: the live orchestrator path needs coverage, not just pure functions.
- **Test-harness order-dependence** — aiosqlite + StaticPool + pytest-asyncio per-test event loops
  caused `no such table: teams` once async tests were added. Fixed with a shared-cache in-memory DB +
  process-lifetime keepalive connection; suite now order-independent (**93 tests pass**).
- **SSR hydration mismatch** — session/localStorage-driven nav islands were SSR'd (`client:load`),
  mismatching the client; switched to `client:only="react"`.
- **API base resolution** — env var (Vercel `vercel.json`) wins; else host-based (localhost -> local
  backend, else `gitsyntropy.onrender.com`), so a deployed build can never accidentally call
  localhost and local never calls prod.

---

## 7. Reproduce every metric (defend the numbers live)

```bash
cd apps/backend
uv run python ../../scripts/eval_recommender.py     # NDCG/hit-rate/coverage -> docs/recommender_eval.md
uv run python ../../scripts/calibration_evidence.py # ECE before/after Platt -> docs/calibration_evidence.md + .png
uv run python ../../scripts/cat_ablation.py         # adaptive vs fixed + ICC -> docs/cat_ablation.* , docs/irt_icc.*
uv run python -m pytest -q                          # 93 passed
```
Local demo data (recommender panel / trace view): `uv run python ../../scripts/seed_demo.py`
(local SQLite only; `--clear` to remove).

---

## 8. 30-second elevator version

"GitSyntropy decomposes engineering-team fit into 8 weighted psychometric dimensions, each scored by
an IRT adaptive assessment plus GitHub behavioural signals, with Platt-calibrated confidence
(ECE 0.375 -> 0.0099). On top I built a reciprocal teammate recommender — harmonic-mean directional
fit, content-based vs matrix-factorization, benchmarked NDCG@5 0.90 with an honest
accuracy-vs-coverage / cold-start analysis. The whole pipeline runs as a LangGraph multi-agent system
with a persisted, replayable per-node trace. It is deployed (Vercel + Render + Supabase), tested
(93 passing, order-independent), and every number is reproducible from a script in the repo."
