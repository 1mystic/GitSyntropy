# GitSyntropy — Phased Implementation Plan

> **Before starting any phase:** Read `CONTEXT.md` first.  
> **After completing any task:** Update `CONTEXT.md` changelog + mark the task done here.

---

## Phase 0 — Security (Do This Before Any Public Release)

**Goal:** Close the 4 P0 security holes. Nothing should ship publicly until these are done.

| Task | Owner | Prompt | Status |
|---|---|---|---|
| P0-1: Add auth guards to team endpoints | Claude Code | See below | ⬜ |
| P0-2: Add ownership validation (user_id from JWT, not body) | Claude Code | See below | ⬜ |
| P0-3: Encrypt GitHub access tokens at rest | Claude Code | See below | ⬜ |
| P0-4: Add rate limiting + auth to user search | Claude Code | See below | ⬜ |

### P0-1: Auth Guards for Team Endpoints

In `apps/backend/app/main.py`, add `claims: dict = Depends(_decode_token_claims)` to every team route:
```python
@app.post(f"{settings.api_prefix}/teams", ...)
async def create_team_route(payload, claims=Depends(_decode_token_claims), db=Depends(get_db)):
    # Use claims["sub"] as created_by, ignore payload.created_by
```

Routes to fix: `POST /teams`, `PATCH /teams/{id}`, `POST /teams/{id}/members`, `DELETE /teams/{id}/members/{user_id}`.

### P0-2: Ownership Validation

For `/github/sync`, `/assessment/responses`, `/orchestrator/run` — the `user_id` must come from the JWT, not the request body:
```python
async def github_sync(request, payload, claims=Depends(_decode_token_claims), db=Depends(get_db)):
    user_id = str(claims["sub"])  # not payload.user_id
```

### P0-3: Encrypt GitHub Tokens

Use `cryptography.fernet` with a derived key from `GS_JWT_SECRET`. Store as `Fernet.encrypt(token.encode()).decode()`. Add a `decrypt_access_token()` helper that `get_user_profile` consumers call.

### P0-4: Auth + Rate Limit User Search

Add `@limiter.limit("30/minute")` and require a valid JWT bearer token on `GET /users/search`.

---

## Phase 1 — CI / Testing (Make CI Green)

**Goal:** CI must pass before any merge. Currently: 2 tests, 80% coverage gate that cannot pass.

| Task | Owner | Status |
|---|---|---|
| P1-1: Add DB fixture using SQLite for tests | Claude Code | ⬜ |
| P1-2: Write tests for auth, github_sync, assessment, orchestrator | Claude Code | ⬜ |
| P1-3: Drop coverage gate to 60% or use SQLite for in-memory DB | Claude Code | ⬜ |
| P1-4: Add frontend type-check step to CI | Claude Code | ⬜ |

**Key insight:** Replace async PostgreSQL with `aiosqlite` + `create_engine("sqlite+aiosqlite:///:memory:")` in test fixtures. This avoids needing a real DB in CI.

---

## Phase 2 — Data Pipeline Hardening

**Goal:** Make the ML pipeline production-grade, not demo-grade.

| Task | Owner | Delegate To | Status |
|---|---|---|---|
| P2-1: Add `is_mock` flag to GithubSyncResponse | Claude Code | — | ⬜ |
| P2-2: Fix collaboration index — scan contributed repos too | Claude Code | — | ⬜ |
| P2-3: Add GitHub API rate-limit handling with exponential backoff | Claude Code | — | ⬜ |
| P2-4: Fix Monte Carlo seeding — use entropy from team state | Claude Code | — | ⬜ |
| P2-5: Multi-user GitHub sync in orchestrator | Claude Code | — | ⬜ |
| P2-6: Add data versioning schema (source, date, license, version) | Claude Code | — | ⬜ |

### P2-1 Details

Add `is_mock: bool = False` to `GithubSyncResponse` schema and set it `True` in `_mock_github_profile`. Frontend should show a "⚠ Estimated data" badge when `is_mock=True`.

### P2-4 Details

Replace `random.Random(42)` with `random.Random(int(hashlib.md5(str(sorted(team_scores)).encode()).hexdigest(), 16) % (2**32))` — deterministic per team state but unique across configurations.

### P2-5 Details

Refactor `_github_analyst_node` to iterate over all `member_profiles` and fetch/sync GitHub data for each member that doesn't have a completed GithubProfile in DB.

---

## Phase 3 — ML Rigor (Make Claims Match Reality)

**Goal:** Replace heuristic-dressed-as-ML with defensible implementations.

| Task | Owner | Delegate To | Status |
|---|---|---|---|
| P3-1: Replace CAT with IRT-based selection (3PL model) | Claude Code | GPT-4 for math | ⬜ |
| P3-2: Calibrate confidence outputs with Platt scaling | Claude Code | — | ⬜ |
| P3-3: Add evaluation report (calibration, AUC, bias checks) | Claude Code | Gemini for analysis | ⬜ |
| P3-4: Add model registry + artifact versioning | Claude Code | — | ⬜ |
| P3-5: Create benchmark baseline comparison | Claude Code | Qwen for dataset | ⬜ |

### P3-1 Details — True CAT with IRT

The 3-parameter logistic (3PL) IRT model: `P(θ) = c + (1-c) / (1 + exp(-a*(θ-b)))`

Where: θ = current latent trait estimate, a = discrimination, b = difficulty, c = guessing

Algorithm:
1. Initialize θ = 0 (neutral)
2. After each answer, update θ using Newton-Raphson or EAP estimation
3. Select next question that maximizes Fisher information at current θ
4. Stop when SEM(θ) < 0.30 or all questions answered

**Delegate to GPT-4:** Use the prompt in `AGENT_PROMPTS.md → P3-1` to get the IRT implementation.

### P3-3 Details — Evaluation Report

Create `docs/evaluation_report.md` with:
- Dataset description (what GitHub profiles were analyzed)
- Calibration plot (predicted confidence vs observed accuracy)
- Bias analysis (UTC timezone skew, bot account detection)
- Dimension correlation matrix

**Delegate to Gemini Advanced:** Use prompt in `AGENT_PROMPTS.md → P3-3`.

---

## Phase 4 — Real-Time Streaming (Fix the Claude Pipeline)

**Goal:** Make Claude synthesis genuinely stream token-by-token to the browser.

| Task | Owner | Status |
|---|---|---|
| P4-1: Refactor synthesis node to yield tokens via async generator | Claude Code | ⬜ |
| P4-2: Update WebSocket handler to forward streaming tokens | Claude Code | ⬜ |
| P4-3: Update frontend to render streamed tokens progressively | Claude Code | ⬜ |

### P4-1 Details

The synthesis node in `services.py` should NOT collect all tokens. Instead, create a new streaming orchestrator path:

```python
async def stream_synthesis_to_websocket(compat, github_signals, assessment_profile, websocket):
    async for token in stream_synthesis(compat, github_signals, assessment_profile):
        await websocket.send_json({"type": "synthesis_token", "token": token})
```

This requires restructuring how the WebSocket handler interacts with LangGraph — instead of using `graph.astream()` and collecting the synthesis result, synthesis should be called directly after the graph reaches that node.

### P4-3 Details

Frontend `InsightsClient` and `DashboardClient` should accumulate `synthesis_token` events into a local string state and render it progressively with a blinking cursor.

---

## Phase 5 — Persistence & Sharing

**Goal:** Reports should be DB-backed and shareable.

| Task | Owner | Status |
|---|---|---|
| P5-1: Use `TeamScore` DB records for report display | Claude Code | ⬜ |
| P5-2: Add `GET /api/v1/teams/{id}/scores` endpoint | Claude Code | ⬜ |
| P5-3: Add report sharing via invite_token | Claude Code | ⬜ |
| P5-4: Remove localStorage as primary report store | Claude Code | ⬜ |

---

## Phase 6 — Observability & Production Hardening

**Goal:** Visibility after deployment.

| Task | Owner | Delegate To | Status |
|---|---|---|---|
| P6-1: Add structured logging with request IDs | Claude Code | — | ⬜ |
| P6-2: Add Sentry error tracking | Claude Code | — | ⬜ |
| P6-3: Add pipeline step latency metrics | Claude Code | — | ⬜ |
| P6-4: Add CSP headers (remove unsafe-inline) | Claude Code | — | ⬜ |
| P6-5: API versioning + response schema docs | Claude Code | Gemini | ⬜ |

---

## Phase 7 — UX Polish & Truthfulness

**Goal:** UI that's honest about uncertainty and doesn't overclaim.

| Task | Owner | Status |
|---|---|---|
| P7-1: Show "Estimated data" badge when is_mock=true | Claude Code | ⬜ |
| P7-2: Add "Research preview" disclaimer on compatibility scores | Claude Code | ⬜ |
| P7-3: Fix DIMENSION_LABELS to match everywhere (remove Vedic from API) | Claude Code | ⬜ |
| P7-4: Hire simulation UI on compatibility page (stated as in-progress in README) | Claude Code | ⬜ |
| P7-5: Demo mode with clearly synthetic data | Claude Code | ⬜ |

---

## Agent Delegation Strategy

### Use Claude Code (this agent) for:
- All code edits, file writes, bug fixes
- FastAPI route changes, SQLAlchemy models
- React/TypeScript component changes
- Test writing, CI configuration

### Delegate to GPT-4 / ChatGPT for:
- IRT math derivations (P3-1)
- Complex statistical calibration formulas (P3-2)
- Academic-quality documentation of methodology

### Delegate to Gemini Advanced for:
- Large document analysis (evaluation report P3-3)
- API documentation generation (P6-5)
- Bias analysis across a dataset

### Delegate to Qwen / other OSS for:
- Benchmark dataset generation (P3-5)
- Data preprocessing scripts

**See `AGENT_PROMPTS.md` for ready-made prompts for each delegation.**

---

## Session Protocol

Every session working on this project should:

1. **Start:** Read `CONTEXT.md` + this file
2. **Pick a task:** Choose the lowest-phase incomplete task
3. **Work:** Make changes, test locally if possible
4. **End:** Update `CONTEXT.md` changelog with exactly what changed and what's next

Every Claude subagent spawned for this project should receive the contents of `CONTEXT.md` in its briefing.
