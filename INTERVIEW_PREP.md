# GitSyntropy — Deep Technical Interview Preparation

> **How to use this file:** Start with Part 1 (top-level overview) to anchor the narrative. Use Part 2 onward when the interviewer drills into a specific subsystem. Every claim here maps to a real file in the repo — nothing is invented.
>
> **➡ The 2026 upgrade work (reciprocal recommender, calibration evidence with ECE numbers, CAT ablation, agent observability, bug-fix stories) is in Part 19, and all the upgrade formulas are in the Part 20 Math Appendix. That is where the measured metrics live — rehearse it.**

---

## Part 1 — Project Summary

### What is GitSyntropy?

GitSyntropy is a multi-agent SaaS platform that scores the **behavioral compatibility** of software engineering teams. It ingests two data streams — **GitHub commit/PR behavioral data** and **psychometric self-assessments** — and runs them through an **8-dimension weighted psychometric compatibility model**. The result is a team health score out of 36, a dimension-level breakdown, risk flags, and a Claude-generated narrative report.

**Core value proposition:** A team lead uploads their GitHub handles, takes an 8-question adaptive assessment, and receives: "Your team scores 24/36. Chronotype sync is your weakest link — schedule pairing sessions for 10–11 AM, not 4 PM."

### The Problem It Solves

- Engineering teams fail for reasons that aren't visible in task trackers — mismatched working rhythms, communication styles, decision-making frameworks
- Existing tools (DISC, MBTI) are static questionnaires with no behavioral grounding
- GitSyntropy fuses **objective GitHub signals** (when you code, how you collaborate) with **self-reported psychometrics** to get a two-source view

---

## Part 2 — Tech Stack

| Layer | Technology | Why This Choice |
|---|---|---|
| Backend API | FastAPI (Python 3.12) | Native async, excellent OpenAPI generation, Python type hints throughout |
| ORM | SQLAlchemy 2.0 async (`asyncpg`) | Typed `Mapped[]` columns, async sessions, no N+1 by default |
| Database | PostgreSQL (Supabase) / SQLite (tests) | JSONB for nested score vectors; SQLite for zero-config CI |
| ML / Stats | scikit-learn, NumPy | Logistic regression for Platt scaling; NumPy for IRT grid |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) | Streaming narrative synthesis via `messages.stream()` |
| Agent orchestration | LangGraph (StateGraph) | Directed acyclic graph with typed state, step isolation, async nodes |
| Crypto | `cryptography` (Fernet + PBKDF2HMAC) | Authenticated symmetric encryption for stored OAuth tokens |
| Auth | HS256 JWT via `python-jose` | Stateless, works with Supabase auth, `sub` claim is the canonical user_id |
| Rate limiting | slowapi | Per-route limits, memory backend, attaches to FastAPI middleware |
| Frontend | Astro 4 (static) + React islands | Islands architecture: static HTML by default, interactive components hydrated on-demand |
| Frontend state | nanostores | Tiny (< 1 KB) reactive stores; no Redux overhead for a handful of global signals |
| Frontend animation | Framer Motion | Declarative animation primitives, `AnimatePresence` for route transitions |
| CI | GitHub Actions | Backend: pytest + coverage gate; Frontend: `astro check` (TypeScript) + build |
| Deployment | Koyeb (backend), Vercel (frontend) | Backend: Docker container from `Procfile`; Frontend: static CDN |

---

## Part 3 — System Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser (Astro + React islands)                        │
│  ┌──────────┐ ┌─────────────────┐ ┌────────────────┐   │
│  │Dashboard │ │CompatibilityUI  │ │InsightsClient  │   │
│  └────┬─────┘ └────────┬────────┘ └───────┬────────┘   │
│       │  REST           │  REST             │ REST/WS   │
└───────┼─────────────────┼───────────────────┼───────────┘
        │                 │                   │
        ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI  (main.py — routes + middleware)                │
│  ┌─────────────────┐   ┌──────────────────────────────┐ │
│  │ JWT Auth Guard  │   │ Rate Limiter (slowapi)        │ │
│  │ _decode_token_  │   │ 10/min orchestrator           │ │
│  │ claims()        │   │ 5/min candidate sim           │ │
│  └────────┬────────┘   └──────────────────────────────┘ │
│           │                                              │
│  ┌────────▼────────────────────────────────────────────┐│
│  │ services.py (business logic)                        ││
│  │ ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌────────┐ ││
│  │ │ IRT CAT  │ │Monte Carlo│ │LangGraph │ │Compat  │ ││
│  │ │  3PL     │ │ Simulator │ │ Pipeline │ │ Engine │ ││
│  │ └──────────┘ └───────────┘ └────┬─────┘ └────────┘ ││
│  └─────────────────────────────────┼───────────────────┘│
│                                    │                     │
│  ┌────────────────────────────────▼──────────────────┐  │
│  │ LangGraph StateGraph (async nodes)                 │  │
│  │ START → github_analyst → psychometric_profiler     │  │
│  │       → [candidate_simulation] → compatibility_eng │  │
│  │       → synthesis → END                            │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ calibration  │  │ crypto.py    │  │ claude_client │  │
│  │ (Platt logr) │  │ (Fernet enc) │  │ (stream API)  │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ SQLAlchemy async ORM + PostgreSQL / SQLite        │   │
│  │ Tables: user_profiles, github_profiles,           │   │
│  │         psychometric_profiles, teams,             │   │
│  │         team_members, agent_runs, team_scores     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### WebSocket Flow (Critical Path)

```
POST /orchestrator/run  →  create AgentRun in DB  →  return run_id

WS /ws/analysis/{run_id}
  ├── Accept connection
  ├── Load AgentRun (team_id, user_id, include_candidates)
  ├── Decrypt stored OAuth token
  ├── stream_orchestrator_updates() yields {step_name: step_data}
  │     ├── github_analyst completes → send {step, status: "completed"}
  │     ├── psychometric_profiler completes → send event
  │     ├── compatibility_engine completes → capture latest_compat
  │     └── synthesis:
  │           ├── stream_synthesis() → async for token → send {type: "synthesis_token"}
  │           └── save_team_score() → persist to DB
  └── send {step: "orchestration", status: "completed"} → close
```

---

## Part 4 — Directory Structure

```
GitSyntropy/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py          # FastAPI routes, WebSocket handler, middleware
│   │   │   ├── services.py      # All business logic: IRT, Monte Carlo, LangGraph
│   │   │   ├── models.py        # SQLAlchemy ORM models
│   │   │   ├── schemas.py       # Pydantic request/response models + TRAIT_DIMENSIONS/TRAIT_WEIGHTS constants
│   │   │   ├── calibration.py   # Platt-scaled CalibrationModel (sklearn LogisticRegression)
│   │   │   ├── crypto.py        # Fernet encrypt/decrypt for GitHub OAuth tokens
│   │   │   ├── claude_client.py # Anthropic streaming synthesis client
│   │   │   ├── github_client.py # GitHub REST API client
│   │   │   ├── config.py        # pydantic-settings (GS_ prefixed env vars)
│   │   │   └── database.py      # SQLAlchemy async engine + session factory
│   │   ├── tests/
│   │   │   ├── conftest.py      # SQLite in-memory DB fixture + JWT auth fixture
│   │   │   ├── test_health.py
│   │   │   ├── test_teams.py
│   │   │   ├── test_compatibility.py
│   │   │   ├── test_cat_assessment.py
│   │   │   └── test_coverage_gaps.py
│   │   └── pyproject.toml
│   └── frontend/
│       ├── src/
│       │   ├── components/      # React islands (CompatibilityClient, DashboardClient, etc.)
│       │   ├── lib/
│       │   │   ├── api.ts       # Typed fetch wrappers for every backend endpoint
│       │   │   ├── stores.ts    # nanostores: $session, $teams
│       │   │   └── featureFlags.ts  # AUTH_REQUIRED, PUBLIC_GUEST_TRIAL env booleans
│       │   └── pages/           # Astro .astro pages (SSG)
│       └── package.json
├── .github/workflows/
│   ├── ci.yml    # pytest + coverage, astro check + build
│   └── deploy.yml
├── CONTEXT.md    # Living architecture doc
├── PLAN.md       # Feature roadmap (F1–F10)
└── INTERVIEW_PREP.md  # This file
```

---

## Part 5 — The Scoring Framework (8-Dimension Weighted Psychometric Model)

### What Is It?

The compatibility engine decomposes team fit into **8 orthogonal psychometric dimensions**, each carrying an integer weight from 1 to 8 (summing to a 36-point scale). The weights encode the relative impact of each dimension on team cohesion — chronotype overlap and stress response dominate; innovation-style differences matter least. Each dimension is scored from the adaptive (IRT) assessment plus GitHub behavioural signals, then combined by a variance-based pairwise scorer. The 1–8 weighting is a **design hypothesis**, not an empirically-fitted factor loading — a point worth stating honestly in an interview.

### The 8 Dimensions and Their Weights

| Internal Key | Engineering Meaning | Max Points |
|---|---|---|
| `chronotype_sync` | Overlap in peak productive hours | 8 |
| `stress_response` | How members handle stress/deadlines | 7 |
| `risk_tolerance` | Risk tolerance: bold vs. cautious | 6 |
| `decision_style` | Decision-making: data vs. intuition | 5 |
| `work_style` | Work style and conflict resolution | 4 |
| `team_resilience` | Adaptability, social compatibility | 3 |
| `leadership_orientation` | Leadership / authority orientation | 2 |
| `innovation_drive` | Innovation Drive: creative vs. stability | 1 |

**Total = 1+2+3+4+5+6+7+8 = 36 points**

### Score Computation

Each question is Likert-scale 1–5. The raw answer is normalised to [0, 1] and scaled by dimension weight:

$$\text{score}_d = \frac{(\text{answer} - 1)}{4} \times w_d$$

where $w_d$ is the dimension weight from the table above.

Pairwise compatibility takes the **geometric mean** of two members' normalised scores:

$$\text{dim\_score}_{d} = \frac{\text{score}_{d,A} + \text{score}_{d,B}}{2}$$

The aggregate score is:

$$S_{36} = \sum_{d=1}^{8} \text{dim\_score}_d \leq 36$$

Levels:
- **Excellent**: $S_{36} > 28$ (~78%)
- **Good**: $22 \leq S_{36} \leq 28$
- **Fair**: $18 \leq S_{36} < 22$
- **Poor (high friction)**: $S_{36} < 18$

### Weak / Strong Classification

A dimension $d$ is **weak** if: $\text{dim\_score}_d < 0.3 \times w_d$

A dimension $d$ is **strong** if: $\text{dim\_score}_d > 0.8 \times w_d$

---

## Part 6 — IRT 3-Parameter Logistic Model (CAT Assessment)

### Why IRT Instead of a Fixed Questionnaire?

Classic Likert surveys ask everyone the same 8 questions in fixed order. IRT's advantage: **each subsequent question is chosen to maximally reduce uncertainty about the respondent's latent trait** (their trait level $\theta$). This means some respondents can stop at 5 questions with the same measurement precision as others who need all 8.

### The 3-Parameter Logistic (3PL) Model

The probability that a respondent with trait level $\theta$ endorses item $j$ is:

$$P(X_j = 1 \mid \theta) = c_j + \frac{1 - c_j}{1 + e^{-a_j(\theta - b_j)}}$$

**Parameters:**
- $a_j$ — **discrimination**: how sharply the item separates low from high $\theta$ (steepness of the sigmoid). Higher $a$ = more informative item.
- $b_j$ — **difficulty**: the $\theta$ value at which $P = \frac{1+c}{2}$ (the inflection point). Items with $b$ close to the current $\theta$ estimate are most informative.
- $c_j$ — **pseudo-guessing**: the minimum probability even at $\theta \to -\infty$. Keeps probability bounded away from 0.

**Our IRT parameters (seeded from behavioral research on engineering assessments):**

```python
_IRT_PARAMS = {
    "q1": {"a": 0.65, "b": -2.0, "c": 0.01},   # Chronotype — easy, low discrimination
    "q2": {"a": 0.80, "b": -1.4, "c": 0.01},   # Risk tolerance
    "q3": {"a": 0.95, "b": -0.8, "c": 0.01},   # Work style
    "q4": {"a": 1.10, "b": -0.2, "c": 0.01},   # Decision style
    "q5": {"a": 1.25, "b":  0.5, "c": 0.01},   # Stress response
    "q6": {"a": 1.45, "b":  1.0, "c": 0.01},   # Collaboration
    "q7": {"a": 1.70, "b":  1.6, "c": 0.01},   # Leadership
    "q8": {"a": 2.00, "b":  2.2, "c": 0.01},   # Innovation drive — hardest, highest disc.
}
```

### Fisher Information

The **Fisher Information** $I_j(\theta)$ measures how much information item $j$ provides about $\theta$:

$$I_j(\theta) = \frac{a_j^2 (P_j - c_j)^2}{(1 - c_j)^2 \cdot P_j(1 - P_j)}$$

Intuitively: items are most informative when $P_j$ is near 0.5 (maximum variance in responses) and $a_j$ is high (sharp discrimination). Item $j$ is maximally informative at the $\theta$ where $P_j(\theta) \approx \frac{1+c_j}{2} \approx 0.5$.

**Key numerical result:** At $\theta = 0$ (prior mean, no answers yet), **q2 has the highest Fisher information** (~1.98), not q8 (~0.03). This is because q8's difficulty $b=2.2$ is far from $\theta=0$, making it nearly uninformative at the start. q2 with $b=-1.4$ sits closer to where most respondents begin.

### Expected A Posteriori (EAP) Theta Estimation

After collecting answers, we estimate $\theta$ via Bayesian posterior:

**Prior:** $\theta \sim \mathcal{N}(0, 1)$ discretised over a 81-point grid $\{-4.0, -3.9, \ldots, 4.0\}$

**Likelihood** for observed responses $\{r_j\}$ where $r_j = \frac{\text{answer}_j - 1}{4} \in [0, 1]$:

$$L(\theta) = \prod_{j \in \text{answered}} P_j(\theta)^{r_j} \cdot (1 - P_j(\theta))^{1 - r_j}$$

This is a **continuous-response formulation**: instead of treating the Likert answer as binary correct/incorrect, we treat it as a continuous endorsement level. An answer of 5 (r=1.0) is full endorsement; 1 (r=0.0) is full rejection.

**Posterior:**

$$\pi(\theta_k \mid \text{data}) \propto L(\theta_k) \cdot \mathcal{N}(\theta_k; 0, 1)$$

**EAP estimate:**

$$\hat{\theta} = \sum_{k} \theta_k \cdot \pi(\theta_k \mid \text{data})$$

**Posterior variance and standard error:**

$$\text{Var}(\theta) = \sum_{k} (\theta_k - \hat{\theta})^2 \cdot \pi(\theta_k \mid \text{data})$$
$$\text{SE} = \sqrt{\text{Var}(\theta)}$$

### Early Stopping Rule

The CAT terminates when:
$$\text{SE}(\hat{\theta}) < 0.35$$

This threshold (chosen empirically) corresponds to approximately $\pm 0.35$ logits of precision — sufficient to classify a respondent into one of the 5 Likert categories with high confidence.

**Why this matters:** With midpoint answers (all r=0.5), every item contributes ambiguous likelihood near sqrt(p(1-p)) — maximum entropy — so the posterior stays close to the N(0,1) prior with SE ≈ 1.0 >> 0.35. Early stopping is not triggered with midpoint answers.

### Question Selection Strategy

```python
def cat_select_next_question(current_answers):
    unanswered = [qid for qid in _IRT_PARAMS if qid not in current_answers]
    if not unanswered:
        return None
    theta, se = _eap_theta(current_answers)
    if se < _STOP_SE:   # 0.35
        return None
    return max(unanswered, key=lambda qid: _fisher_info(theta, **_IRT_PARAMS[qid]))
```

**Why the CAT selects q2 first (not q8):** At $\theta=0$, the Fisher information computation yields:

| Question | $I_j(0)$ |
|---|---|
| q2 | ~1.977 |
| q3 | ~1.939 |
| q1 | ~1.562 |
| q4 | ~1.511 |
| q5 | ~0.829 |
| q6 | ~0.478 |
| q7 | ~0.167 |
| q8 | ~0.027 |

q8 is near-useless at $\theta=0$ because its difficulty $b=2.2$ is two standard deviations above the prior mean.

**Empirical ablation on the deployed 8-item bank:** adaptive Fisher-information selection reaches $\text{SE} \le 0.80$ in **4.22** items on average vs **4.23** for fixed order. The honest story here is not a dramatic item-count reduction; it is that the adaptive curve tightens earlier, which is exactly what the ICC plot in `docs/irt_icc.png` shows.

---

## Part 7 — Platt-Scaled Confidence Calibration

### The Problem with Naive Confidence

The naive approach was: $\text{confidence} = \frac{\text{observed signals}}{\text{total signals}}$. This gives exactly 1.0 for full data regardless of whether the scores are extreme or moderate. It has no probabilistic meaning.

### Platt Scaling

**Platt scaling** fits a logistic regression on top of raw classifier scores to produce calibrated probabilities. Here it's used to answer: "Given this score vector and signal coverage, how reliable is the prediction?"

The model is trained on **10,000 synthetic samples** generated at startup:

```python
for _ in range(10_000):
    coverage = rng.uniform(0.1, 1.0)
    latent = rng.normal(0.0, 1.0)       # true underlying compatibility
    noise = rng.normal(0.0, max(0.15, 1.0 - coverage), 8)  # noise scales with missing data
    scores = sigmoid(latent + noise)    # synthetic dimension scores
    scores[~observed_mask] = 0.5        # missing dims set to neutral
    
    # Ground-truth certainty label
    certainty = 2.4*coverage + 1.6/(1+std) + 0.5*|mean-0.5| 
              - 1.8*(1-coverage)*|mean-0.5| + noise
    y = Bernoulli(sigmoid(certainty))
```

**Feature vector** (8 features fed to logistic regression):

$$\mathbf{x} = \left[\bar{s},\ \sigma_s,\ \min_d s_d,\ \max_d s_d,\ \frac{1}{1+\sigma_s},\ c,\ c^2,\ \bar{s} \cdot c\right]$$

where $\bar{s}$ is mean score, $\sigma_s$ is score std, $c$ is signal coverage.

The **interaction term** $\bar{s} \cdot c$ captures the key insight: high average scores with low coverage are still uncertain (the "lucky" outcome problem), while high average scores with full coverage are genuinely confident.

**Low confidence flag trigger:** $\text{confidence} < 0.75$ OR $\text{signal\_coverage} < 0.80$. The second condition was added because the logistic model, trained on synthetic data with moderate average scores, can return confidence > 0.75 even at 62.5% coverage when scores happen to be moderate.

### Why LRU Cache for the Model?

```python
@lru_cache(maxsize=1)
def _get_calibration_model() -> CalibrationModel:
    return CalibrationModel.from_synthetic_data()
```

`from_synthetic_data()` trains sklearn LogisticRegression on 10,000 samples — this takes ~100ms at startup. The `@lru_cache(maxsize=1)` ensures it runs exactly once per process (Python functions are hashable, making this safe for zero-argument callables). The trained model is an immutable object, so thread-safety is not a concern.

---

## Part 8 — Monte Carlo Candidate Simulation

### Purpose

Given the current team's psychometric profiles, find the **ideal next-hire profile** — the candidate dimension vector that maximally improves the team's aggregate compatibility score.

### Algorithm

**Seed**: `MD5(JSON(team_scores))` — deterministic for the same team composition, enabling reproducibility without storing results.

**Biased sampling**: Dimensions where the team mean score < 45% of max weight are identified as "weak":

$$\text{weak\_dims} = \{d : \bar{s}_d < 0.45 \cdot w_d\}$$

For weak dimensions, candidates are sampled in $[0.5, 1.0] \times w_d$ (biased high). For others: $[0.15, 0.95] \times w_d$.

**Improvement metric** (for each iteration $i$):

$$\Delta_i = \frac{1}{|T|}\sum_{m \in T} S_{36}(\text{candidate}_i, m) - \bar{S}_{36}^{\text{internal}}$$

where $\bar{S}_{36}^{\text{internal}}$ is the mean pairwise score within the existing team.

**Output statistics**:
- `mean_improvement`: $\frac{1}{N}\sum_{i=1}^{N} \Delta_i$
- `best_improvement`: $\max_i \Delta_i$ (from the optimal candidate profile)
- `p25_improvement`, `p75_improvement`: interquartile range of $\Delta$ distribution

### Why 1,000 Iterations?

At 1,000 iterations the **standard error of the mean** improvement estimate is:

$$\text{SE}_{\bar{\Delta}} = \frac{\sigma_\Delta}{\sqrt{1000}} \approx \frac{3.0}{\sqrt{1000}} \approx 0.09 \text{ points}$$

Given the score range is [0, 36], 0.09 points is sub-percent precision — sufficient for hiring recommendations. Going to 5,000 (API maximum) reduces SE to ~0.04 points.

---

## Part 9 — LangGraph Multi-Agent Orchestration

### Why LangGraph?

LangGraph is a graph-based state machine for building multi-step agent pipelines. Advantages over a flat function chain:
1. **Typed state** — `OrchestratorState` is a `TypedDict` with known keys; nodes read/write without shared mutable objects
2. **Conditional edges** — `candidate_simulation` node is included only when `include_candidates=True`
3. **Streaming** — `stream_orchestrator_updates()` yields each node's output as it completes, enabling WebSocket step-by-step progress
4. **Isolated failures** — a node can raise without killing the whole graph (wrapped in try/except at WebSocket level)

### Pipeline Structure

```
START
  │
  ▼
github_analyst          # Fetch GitHub signals (real API → DB fallback → mock)
  │
  ▼
psychometric_profiler   # Load stored assessment profile or use neutral midpoints
  │
  ├─── (include_candidates=True) ───▶ candidate_simulation  # Monte Carlo
  │                                          │
  │◀─────────────────────────────────────────┘
  ▼
compatibility_engine    # Pairwise compatibility scores across all team members
  │
  ▼
synthesis               # Claude narrative (streamed via WebSocket)
  │
  ▼
END
```

### State Shape

```python
class OrchestratorState(TypedDict, total=False):
    team_id: str
    user_id: str
    github_handle: str
    access_token: str          # decrypted OAuth token
    include_candidates: bool
    member_profiles: list[dict]  # DB-preloaded before graph starts
    github_signals: dict        # set by github_analyst
    assessment_profile: dict    # set by psychometric_profiler
    candidate_outlook: dict     # set by candidate_simulation
    compatibility: dict         # set by compatibility_engine
    synthesis: dict             # set by synthesis node
    synthesis_text: str         # assembled from streaming tokens
```

`total=False` makes all keys optional — nodes add keys without requiring them all to exist at graph start.

### Real vs Mock Fallback Chain

The `github_analyst` node implements a three-tier fallback:
1. **Real GitHub API** (if OAuth token available) — `GitHubAnalystClient.analyze(handle)`
2. **Preloaded DB data** — sync results stored in `GithubProfile` table from previous syncs
3. **Deterministic mock** — hash-based generation using `len(handle)` as seed

The mock is deterministic so the same handle always produces the same mock metrics, making the UI feel consistent in demo mode.

---

## Part 10 — Security Architecture

### JWT Authentication

**Algorithm:** HS256 (HMAC-SHA256). Claims: `{"sub": user_id, "exp": ..., "iss": "gitsyntropy-local", "github_handle": ...}`

**Guard pattern:**

```python
def _decode_token_claims(authorization: str | None = Header(default=None)) -> dict:
    token = _require_bearer_token(authorization)
    try:
        return decode_jwt(token)
    except (AuthTokenError, ValueError):
        raise HTTPException(status_code=401, ...)
```

**Critical security decision:** `user_id = str(claims["sub"])` — the server **never trusts `user_id` from the request body**. Even if an attacker sends `{"user_id": "admin"}`, the actual user_id is always derived from the JWT signature-verified `sub` claim.

**Protected endpoints:** POST /teams, POST /teams/{id}/members, DELETE /teams/{id}/members/{uid}, PATCH /teams/{id}, POST /github/sync, POST /assessment/responses, POST /orchestrator/run, GET /users/search

**Public endpoints:** GET /teams, GET /teams/{id}, GET /assessment/questions, GET /health

### Fernet Encryption for GitHub OAuth Tokens

GitHub OAuth access tokens are sensitive — they grant read access to a user's entire GitHub data. We encrypt them at rest before writing to the `user_profiles.github_access_token` column.

**Key derivation** (PBKDF2HMAC):

$$K = \text{PBKDF2HMAC\_SHA256}(\text{password}=\text{jwt\_secret},\ \text{salt}=b\text{"gitsyntropy-token-encryption"},\ \text{iterations}=390{,}000,\ \text{len}=32)$$

390,000 iterations is the OWASP 2023 recommendation for PBKDF2-SHA256 (prevents brute-force even if the DB is dumped).

**Fernet** provides:
- AES-128-CBC encryption
- HMAC-SHA256 authentication (prevents tampering)
- Timestamp (prevents replay attacks with stale tokens)

**Migration path:** When decrypting, `try: Fernet.decrypt()` catches `InvalidToken` and falls back to returning the plaintext — this handles tokens stored before encryption was introduced without a DB migration.

### Rate Limiting (slowapi)

| Endpoint | Limit | Rationale |
|---|---|---|
| POST /orchestrator/run | 10/min | LangGraph runs are expensive; prevents abuse |
| POST /github/sync | 10/min | GitHub API has rate limits; prevents cascade |
| POST /candidates/simulate | 5/min | CPU-intensive 1000-iteration Monte Carlo |
| GET /auth/github/start | 30/min | OAuth flow cannot be spammed |
| GET /users/search | 30/min | DB query on user handles |

Key function: `get_remote_address` (IP-based). In production behind a reverse proxy, `X-Forwarded-For` is used.

### Superadmin Guard

```python
def _require_superadmin(authorization) -> dict:
    claims = _decode_token_claims(authorization)
    if not is_superadmin(claims.get("github_handle")):
        raise HTTPException(403, "Superadmin access required")
    return claims
```

`is_superadmin` checks `github_handle.lower() == settings.superadmin_github_handle.lower()`. The superadmin handle is configured at deploy time via `GS_SUPERADMIN_GITHUB_HANDLE` — not hardcoded.

---

## Part 11 — Database Design

### Why SQLAlchemy 2.0 Async?

**Problem:** FastAPI is fully async (ASGI). Traditional SQLAlchemy sync sessions block the event loop during DB I/O. With `asyncpg` + `create_async_engine`, every DB operation yields control to the event loop, allowing thousands of concurrent WebSocket connections.

**Mapped columns** (SQLAlchemy 2.0 style):

```python
class GithubProfile(Base):
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
```

`Mapped[T]` provides type-checker support — if you write `profile.user_id + 1`, mypy catches the int/str mismatch.

### JSONB vs JSON

**PostgreSQL JSONB** (Binary JSON):
- Indexed: `CREATE INDEX USING GIN(raw_data jsonb_path_ops)` works
- Operators: `raw_data @> '{"key": "value"}'` for containment checks
- ~10% read overhead vs JSON (decompression) but dramatically faster for queried fields

**SQLite fallback** (for tests):
```python
_db_url = os.environ.get("GS_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
if "postgresql" in _db_url:
    from sqlalchemy.dialects.postgresql import JSONB
else:
    JSONB = JSON  # type: ignore
```

SQLite doesn't have JSONB — aliasing to `JSON` at the Python level satisfies SQLAlchemy's type system without a schema change.

### Connection Pooling

```python
create_async_engine(
    database_url,
    pool_pre_ping=True,       # verify connection before using from pool
    pool_size=5,              # 5 persistent connections
    max_overflow=10,          # up to 10 additional burst connections
    connect_args={"statement_cache_size": 0},  # asyncpg: disable prepared statement cache
)
```

`statement_cache_size=0` is required for Supabase's pgBouncer connection pooler, which uses session-mode pooling — prepared statements bound to one physical connection would be lost when pgBouncer reassigns the logical connection.

### Session Lifecycle

```python
@asynccontextmanager
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

`expire_on_commit=False` in `async_sessionmaker` means objects don't need to be re-fetched after commit — important because in async contexts, lazy loading is not available.

---

## Part 12 — Frontend Architecture

### Astro Islands Pattern

Astro renders pages as **static HTML by default**. React components are "hydrated" on the client only when `client:load` or `client:visible` directive is used. Benefits:
- Zero JS sent to the browser for non-interactive pages (e.g., the landing page)
- React component trees are isolated — one broken island doesn't crash others
- Server-side rendering + static generation possible per page

**Our interactive components** (React islands):
- `CompatibilityClient.tsx` — pairwise score form + SVG circular progress gauge
- `DashboardClient.tsx` — team dimension chips with dimension label mapping
- `InsightsClient.tsx` — synthesis narrative display with WebSocket event handling
- `WorkspaceClient.tsx` — orchestrator trigger + live WebSocket step progress

### State Management (nanostores)

```typescript
export const $session = atom<Session | null>(null);
export const $teams = atom<Team[]>([]);
```

**Why nanostores over Redux/Zustand?** The app has two global signals — auth session and team list. Redux would add 40KB of boilerplate. nanostores is 274 bytes and framework-agnostic (works in Astro `.astro` files too, not just React).

### WebSocket Handling on Frontend

The synthesis stream arrives as a sequence of events:
```json
{"type": "synthesis_token", "token": " The"}
{"type": "synthesis_token", "token": " team"}
...
{"step": "synthesis", "status": "completed", "data": {...}}
```

The client appends tokens to a local buffer and renders them progressively using React state. When the `synthesis` completion event arrives, the full narrative is available in `step_data` as a fallback.

---

## Part 13 — Streaming Architecture (WebSocket + Anthropic)

### Server-Side Streaming (claude_client.py)

```python
async def stream_synthesis(...) -> AsyncGenerator[str, None]:
    if not settings.anthropic_api_key:
        yield _fallback_synthesis(compatibility)
        return

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    async with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
```

**`AsyncGenerator[str, None]`** — the `None` is the send type (we never send into this generator). This is a pull-based async generator: the caller calls `async for token in stream_synthesis(...)` and the generator suspends between tokens, yielding control to the event loop for other WebSocket messages to be processed.

### WebSocket + Generator Interleaving

```python
async for token in stream_synthesis(compat, github, assessment):
    narrative_parts.append(token)
    await websocket.send_json({"type": "synthesis_token", "token": token})
```

Each `await websocket.send_json` is a `asyncio.Task` checkpoint — other coroutines in the event loop can run between tokens. This gives sub-100ms latency per token from the client's perspective.

### Fallback When API Key Not Set

The `_fallback_synthesis()` returns a deterministic template based on the total score and weak dimensions. This ensures the pipeline always completes even without the Anthropic key configured (useful for local dev/CI).

---

## Part 14 — CI/CD Pipeline

### Backend CI (pytest + coverage)

```yaml
- run: pip install -e ".[dev]" slowapi aiosqlite
- run: pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=65 -q
env:
  GS_DATABASE_URL: "sqlite+aiosqlite:///:memory:"
  GS_JWT_SECRET: ci-test-jwt-secret-not-for-production
```

**Key design decisions:**
- `aiosqlite` + SQLite in-memory: no PostgreSQL needed in CI (Supabase not reachable from GH Actions)
- Coverage gate at 65%: enforces regression tests on all new routes
- `GS_JWT_SECRET` set in CI env: allows `create_jwt()` to work in tests without `.env`

### Frontend CI (Astro check + build)

```yaml
- run: npm run check   # astro check = TypeScript type checking
- run: npm run build   # production build catches import errors
```

`astro check` catches type errors in React island props that `tsc --noEmit` would miss (Astro's `.astro` files have their own type system).

### Test Architecture

**Session-scoped SQLite override:**
```python
_TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # same physical connection across all tests
)
```

`StaticPool` is critical: it forces SQLAlchemy to reuse a single in-memory SQLite connection. Without it, each test would get a new connection and a fresh (empty) database — tests would fail due to missing tables.

**JWT auth fixture:**
```python
@pytest.fixture(scope="session")
def auth_headers():
    token, _ = create_jwt(user_id="test_user", github_handle="test_handle")
    return {"Authorization": f"Bearer {token}"}
```

`scope="session"` means the JWT is created once and reused across all 83 tests, avoiding repeated HMAC-SHA256 computations. The JWT is valid for `GS_JWT_EXP_MINUTES` (default 60 minutes) — enough for any CI run.

---

## Part 15 — Probable Tough Interview Questions

### On IRT

**Q: Why not just use the highest-weight question first?**

The old algorithm did this. The problem: q8 (nadi/chronotype, weight=8) has IRT difficulty $b=2.2$, meaning it maximally discriminates respondents with $\theta \approx 2.2$ (high end). At the start, with no prior information, we assume $\theta \sim \mathcal{N}(0,1)$. q8's Fisher information at $\theta=0$ is 0.027 — nearly zero — because almost nobody at the center of the trait distribution is near the item's difficulty. Asking q8 first wastes the first response.

**Q: How did you choose $b$ values for the items?**

The $b$ values form an approximately uniform spread across the trait range: $\{-2.0, -1.4, -0.8, -0.2, 0.5, 1.0, 1.6, 2.2\}$. This ensures at least one item is highly informative at every region of the $\theta$ scale. The discrimination $a$ values increase monotonically (0.65→2.0) to make later-in-sequence items sharper — they're designed for refinement, not first contact.

**Q: What is the difference between EAP and MAP estimation?**

**EAP (Expected A Posteriori):** weighted mean of the posterior: $\hat{\theta}_{EAP} = E[\theta \mid \text{data}]$. Smoother, less sensitive to prior choice, but computationally requires integrating over the full distribution.

**MAP (Maximum A Posteriori):** $\hat{\theta}_{MAP} = \arg\max_\theta \pi(\theta \mid \text{data})$. Equivalent to L2-regularized MLE. Faster but produces biased estimates near the boundaries of the trait range.

We use EAP because the posterior is discretised over 81 grid points — the difference in computational cost is negligible, and EAP is theoretically preferred for CAT.

**Q: Why use continuous-response IRT (scores as real-valued r) rather than binary correct/incorrect?**

Our items are Likert-scale attitude questions, not knowledge items. There's no "correct" answer. Treating a response of 3 as "half-endorsed" (r=0.5) vs fully endorsed or rejected is more informative than collapsing to binary. This is the **graded response model** approximation within the 3PL framework.

**Q: What happens if a respondent tries to game the system by answering 5 on everything?**

With all answers = 5 (r=1.0), the EAP estimate pushes strongly toward $\theta \gg 0$. But in the compatibility engine, extreme scores in any single direction produce **high dimension scores for one person but create poor pairwise compatibility** when compared with team members who have moderate scores. A "game" of 5/5/5/... produces `dim_score = max_weight * 1.0` for every dimension. The pairwise score averages the two members' scores, so $\text{dim\_score}_d = \frac{w_d \cdot 1.0 + w_d \cdot 0.5}{2} = 0.75 \cdot w_d$, which is actually "strong" — but the score is entirely a function of the other member's scores, not inflated by the gamer alone.

---

### On Calibration

**Q: Is Platt scaling the right approach here? Why not isotonic regression or temperature scaling?**

Platt scaling (logistic regression on features) was chosen because:
1. The feature vector has 8 hand-crafted features with interpretable semantics — a parametric model is appropriate
2. The dataset is synthetic (we control the ground truth), so fitting a logistic model on 10,000 samples is reliable
3. Isotonic regression is non-parametric and requires sorted data; it would overfit on 10,000 samples (no regularization)
4. Temperature scaling is a single-parameter recalibration applied after training — it doesn't allow the model to learn that high coverage + high mean score → higher confidence (the interaction effect)

**Q: Your model trains on synthetic data. How do you know it generalizes to real data?**

This is a valid weakness. The synthetic data generation assumes a specific generative model (sigmoid of latent Gaussian + additive noise). Real psychometric data may have non-Gaussian distributions, floor/ceiling effects, and response styles (acquiescence bias). The mitigation:
1. The calibration is applied post-hoc — even if the absolute probability is off, the relative ordering (more complete data = higher confidence) is preserved
2. The low-confidence flag has a hard coverage threshold (`signal_coverage < 0.80`) that doesn't depend on the model at all
3. Future work: fit the model on real compatibility pairs with known outcomes

**Q: What metric validates the calibration model?**

The model provides a `calibration_plot_data()` method that computes the **calibration curve** — binning predicted probabilities and comparing to observed frequencies. A perfectly calibrated model has predicted ≈ observed in every bin. We don't have real evaluation data yet; this is acknowledged as an open item.

---

### On Security

**Q: Your Fernet key is derived from `jwt_secret` with a static salt. Why not a random salt per token?**

A random per-token salt would require storing the salt alongside the ciphertext. For OAuth tokens stored in the DB, this would require an extra column or embedding the salt in the ciphertext blob. Fernet's output already includes a timestamp and HMAC, providing ciphertext uniqueness. The static salt is acceptable here because:
1. The password (`jwt_secret`) is never exposed (it's a deployment secret, not a user password)
2. PBKDF2 with 390,000 iterations makes brute-forcing the key from the salt computationally infeasible even if the salt is known
3. The real threat model is DB dump → token exposure, not key derivation attacks

**Q: Why HS256 for JWTs and not RS256?**

HS256 (HMAC-SHA256) requires a shared secret between signer and verifier — both are the same service in our architecture, so there's no key distribution problem. RS256 (RSA) is preferred when external parties need to verify tokens (e.g., third-party services that can't access our secret). Since all verification happens within our own FastAPI service, the complexity of RS256 (key pairs, rotation, JWKS endpoint) isn't justified.

**Q: What prevents a user from calling POST /orchestrator/run as another user?**

The endpoint signature:
```python
async def orchestrator_run(request, payload: OrchestratorRunRequest, claims=Depends(_decode_token_claims)):
    user_id = str(claims["sub"])  # from JWT, not payload
```
The JWT is signed with `jwt_secret` — a secret only the server knows. Even if a user intercepts another user's run_id, they can only observe the WebSocket stream; they cannot inject their own user_id into the JWT.

---

### On Architecture

**Q: Why did you choose LangGraph over a plain async function chain?**

A plain function chain `result = await step1(state); result2 = await step2(result)` would work but has problems:
1. No built-in conditional routing (skip step based on state)
2. No streaming intermediate results without manual yield
3. State mutations are implicit — hard to test individual nodes in isolation
4. Adding a new step requires modifying the orchestrator function, breaking the open/closed principle

LangGraph's `StateGraph` gives us: explicit edges (routing), typed state (TypedDict), built-in async support, and `astream()` that emits each node's output as it completes — which maps directly to the WebSocket step events.

**Q: Your WebSocket doesn't require JWT auth. Is that a security issue?**

Yes, partially. The `run_id` (a UUID) acts as a capability token — you need to know the run_id to connect. The run_id is returned only to the authenticated user who called `POST /orchestrator/run`. An attacker without the run_id cannot connect. However, if a run_id is leaked (e.g., in browser history), an unauthenticated client could observe the WebSocket stream. Mitigation in future work: require a short-lived token query parameter for WebSocket upgrade.

**Q: Why does `create_tables()` run in the background after startup?**

```python
@asynccontextmanager
async def lifespan(_: FastAPI):
    asyncio.ensure_future(create_tables())
    yield
```

`asyncio.ensure_future` schedules `create_tables()` as a task that runs *after* the server starts accepting connections. This ensures the port binds immediately even if the DB is slow. The real tables are already created in Supabase — `create_tables()` is purely a safety net for local dev. If it's slow, no request is delayed because it runs independently.

**Q: How do you handle the SQLite ↔ PostgreSQL JSONB incompatibility?**

At **import time** in `models.py`, we check `os.environ.get("GS_DATABASE_URL")`. If it contains "postgresql", we import `JSONB` from `sqlalchemy.dialects.postgresql`. Otherwise, we alias `JSONB = JSON`. The key insight: the failure is not at import time (JSONB always imports successfully) but at **table compilation time** when SQLAlchemy tries to emit `JSONB` DDL to SQLite, which doesn't understand it. The environment check happens before any engine is created.

**Q: You use `StaticPool` in tests. What would happen without it?**

SQLite's in-memory database (`:memory:`) is tied to a single connection. When `StaticPool` is not used, SQLAlchemy creates a new connection for each `AsyncSession`. A new connection to `:memory:` creates a **new, empty database** — the tables created in `override_db_dependency` would not exist for the new connection. `StaticPool` with `check_same_thread=False` ensures all connections go through the same physical SQLite connection.

---

### On Frontend

**Q: Why Astro instead of Next.js?**

GitSyntropy's pages are mostly static with occasional interactive components (forms, charts). Next.js is optimized for server-rendered React where every page needs JS. Astro gives us:
1. Zero JS by default — landing page, marketing pages ship 0 KB of JS
2. Islands hydration only where needed
3. Framework-agnostic — we could mix React and Svelte islands if needed
4. Simpler static export for CDN deployment (no Next.js server required)

**Q: nanostores vs React Context for global state?**

React Context re-renders every subscriber when the value changes. For `$session` (auth state), any component reading context would re-render on every auth state change — including deeply nested components. nanostores uses a signal/subscriber model: only components explicitly subscribed with `useStore($session)` re-render. More importantly, nanostores works outside React (in plain `.astro` files), allowing auth state to be checked before island hydration.

---

## Part 16 — Performance and Scalability

| Concern | Current approach | Scale limit |
|---|---|---|
| DB connection pool | 5 persistent + 10 overflow | ~15 concurrent DB queries |
| Rate limiting | In-memory (per-process) | Single instance only; Redis needed for multi-instance |
| CalibrationModel | LRU-cached, fits once at startup | One model per process; fine for single instance |
| Monte Carlo | 1000 iter × O(n_team²) compat calls | Quadratic in team size; acceptable up to ~20 members |
| IRT grid | 81 θ points × n_answers per request | O(n_questions × n_answered); negligible |
| WebSocket | 1 coroutine per connection | Limited by event loop, not DB |
| LangGraph | Async nodes on event loop | CPU-bound nodes (Monte Carlo) block the loop |

**Critical known limitation:** Monte Carlo's inner loop calls `compatibility()` synchronously ~1000 times. This blocks the event loop for ~50–200ms. The fix would be to run it in a `ProcessPoolExecutor` with `asyncio.get_event_loop().run_in_executor()`. Currently acceptable because it's rate-limited to 5/min.

---

## Part 17 — Local Dev Setup (Exact Commands)

### Backend

```bash
cd apps/backend

# 1. Install uv if not present
pip install uv

# 2. Create venv and install all deps including dev extras
uv sync --extra dev

# 3. Create .env (copy from example or create manually)
cat > .env << 'EOF'
GS_DATABASE_URL=sqlite+aiosqlite:///./dev.db
GS_JWT_SECRET=local-dev-secret-change-me
GS_ANTHROPIC_API_KEY=sk-ant-...   # optional
GS_GITHUB_CLIENT_ID=local-dev
GS_GITHUB_CLIENT_SECRET=
GS_FRONTEND_URL=http://localhost:4321
EOF

# 4. Run the server
uv run uvicorn app.main:app --reload --port 8000

# 5. Run tests (SQLite in-memory, no .env needed)
uv run --extra dev pytest tests/ -q --cov=app --cov-fail-under=65
```

### Frontend

```bash
cd apps/frontend

# 1. Install dependencies
npm ci

# 2. Create .env (public vars, checked into git is fine)
cat > .env << 'EOF'
PUBLIC_API_BASE=http://localhost:8000/api/v1
PUBLIC_WS_BASE=ws://localhost:8000
PUBLIC_AUTH_REQUIRED=false
PUBLIC_GUEST_TRIAL=true
EOF

# 3. Dev server (hot reload)
npm run dev   # → http://localhost:4321

# 4. Type check only
npm run check

# 5. Production build
npm run build
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok","service":"GitSyntropy API","version":"0.1.0"}
```

---

## Part 18 — Glossary of All Technical Terms Used

| Term | Definition |
|---|---|
| IRT | Item Response Theory — probabilistic framework modeling the relationship between latent trait and item response probability |
| 3PL | 3-Parameter Logistic — IRT model with discrimination (a), difficulty (b), pseudo-guessing (c) |
| CAT | Computerized Adaptive Testing — sequential test where each item is chosen to maximize Fisher information at current θ estimate |
| EAP | Expected A Posteriori — Bayesian point estimate of θ as the posterior mean |
| Fisher Information | $I(\theta) = E[(\partial \log L / \partial \theta)^2]$ — measures how much information an item provides about θ |
| SE | Standard Error — posterior standard deviation; the CAT stops when SE < 0.35 |
| Platt Scaling | Fitting logistic regression on classifier outputs to produce calibrated probabilities |
| PBKDF2HMAC | Password-Based Key Derivation Function 2 — converts a passphrase into a cryptographic key |
| Fernet | Symmetric authenticated encryption scheme (AES-128-CBC + HMAC-SHA256) from `cryptography` library |
| LangGraph | Library for building stateful multi-agent pipelines as directed graphs |
| JSONB | Binary JSON column type in PostgreSQL — indexable and queryable |
| StaticPool | SQLAlchemy pool that uses a single database connection — required for `:memory:` SQLite in tests |
| nanostores | Tiny reactive state management library (~274 bytes) for Astro/React/plain JS |
| Islands Architecture | Web rendering pattern: static HTML by default, interactive JS injected only in isolated "islands" |
| Signal Coverage | Fraction of total possible data signals that are non-null: $\frac{\text{observed}}{\text{total possible}}$ |
| Monte Carlo | Stochastic optimization: sample random candidates 1000x, track which improves team compatibility most |
| asyncpg | High-performance async PostgreSQL driver; replaces psycopg2 in async contexts |
| AsyncGenerator | Python type for async functions that `yield` — enables pull-based streaming |
| `lru_cache(maxsize=1)` | Cache the single return value of a zero-argument function; used for singleton model initialization |
| Weighted compatibility model | 8 orthogonal psychometric dimensions, integer-weighted 1–8 (36-pt scale); weights are a design hypothesis, not empirically fitted |

---

## Part 19 — 2026 Upgrade Deep-Dive (Recommender · Evidence · Observability)

### 19.1 Reciprocal Recommendation Engine (`app/recommender.py`)

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

### 19.2 Calibration Evidence (`scripts/calibration_evidence.py`)

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

### 19.3 CAT Ablation + ICC (`scripts/cat_ablation.py`)

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

### 19.4 Agent Observability — persisted trace (`agent_runs.agent_events`)

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

### 19.5 Naming Decision — neutral psychometric model

The 8 dimensions were refactored from Vedic-Ashtakoot-derived keys to neutral slugs
(`innovation_drive` ... `chronotype_sync`) across code, tests, prompts, and interview docs, with a
read-time shim (`normalize_dimension_keys`) + migration `0001` preserving stored data. **Why it
matters:** a reviewer reading astrology-derived identifiers could dismiss the genuine IRT/Platt rigor
as pseudoscience. The model is framed honestly as a **multi-criteria weighted psychometric model**
whose 1-8 weights are a **stated design hypothesis**, not an empirically-fitted factor loading; the
calibration layer quantifies trust in each score.

---

### 19.6 Engineering-maturity stories ("tell me about a bug you fixed")

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

### 19.7 Reproduce every metric (defend the numbers live)

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

### 19.8 30-second elevator version

"GitSyntropy decomposes engineering-team fit into 8 weighted psychometric dimensions, each scored by
an IRT adaptive assessment plus GitHub behavioural signals, with Platt-calibrated confidence
(ECE 0.375 -> 0.0099). On top I built a reciprocal teammate recommender — harmonic-mean directional
fit, content-based vs matrix-factorization, benchmarked NDCG@5 0.90 with an honest
accuracy-vs-coverage / cold-start analysis. The whole pipeline runs as a LangGraph multi-agent system
with a persisted, replayable per-node trace. It is deployed (Vercel + Render + Supabase), tested
(93 passing, order-independent), and every number is reproducible from a script in the repo."


---

## Part 20 — Math Appendix (full formulas — defend these on a whiteboard)

All symbols use the 8 dimensions $d \in \{1,\dots,8\}$ with fixed integer weights
$w_d \in \{1,\dots,8\}$ (`TRAIT_WEIGHTS`).

### 20.1 Trait vector (`scores_to_vector`)
Raw stored score $r_d$ (a dimension's value, max $w_d$) is normalised to a common $[0,1]$ scale and
missing dims imputed at the neutral midpoint:
$$ v_d = \mathrm{clip}\!\left(\frac{r_d}{w_d},\,0,\,1\right), \qquad v_d = 0.5 \text{ if } r_d \text{ missing.} $$

### 20.2 Salience (`_salience`) — why fit is asymmetric
The seeker's per-dimension importance blends the global weight with the seeker's own emphasis, then
normalises to a probability vector:
$$ \mathrm{sal}_d(s) = \frac{w_d\,(0.5 + s_d)}{\sum_{j=1}^{8} w_j\,(0.5 + s_j)}, \qquad \sum_d \mathrm{sal}_d(s) = 1. $$
The $0.5$ floor guarantees a zero-score dimension still carries its global weight. Because salience
depends on the seeker $s$, the directional fit below is **asymmetric**.

### 20.3 Directional fit (`directional_fit`)
How well candidate $c$ satisfies seeker $s$ — salience-weighted per-dimension similarity:
$$ \mathrm{fit}(s \to c) = \sum_{d=1}^{8} \mathrm{sal}_d(s)\,\bigl(1 - |s_d - c_d|\bigr) \in [0,1]. $$
Since $\mathrm{sal}(s)$ sums to 1 and each similarity term is in $[0,1]$, the fit is a convex
combination, hence in $[0,1]$. In general $\mathrm{fit}(a\to b)\neq \mathrm{fit}(b\to a)$.

### 20.4 Reciprocal score (`reciprocal_score`) — why harmonic mean
$$ \mathrm{score}(a,b) = \mathrm{HM}\bigl(\mathrm{fit}(a\to b),\,\mathrm{fit}(b\to a)\bigr)
   = \frac{2\,\mathrm{fit}(a\to b)\,\mathrm{fit}(b\to a)}{\mathrm{fit}(a\to b) + \mathrm{fit}(b\to a)}. $$
Key property: $\mathrm{HM}(x,y) \le \min(x,y)\cdot 2 \cdot \tfrac{\max}{x+y}$, and more usefully
$\mathrm{HM}(x,y)\le \mathrm{GM}(x,y)=\sqrt{xy}\le \mathrm{AM}(x,y)$, with equality only when $x=y$.
So a lopsided match ($x \gg y$) is pulled toward the smaller value — the reciprocal requirement.
Example: fit $0.9$ one way, $0.3$ the other $\Rightarrow$ HM $=2(0.9)(0.3)/1.2 = 0.45$, far below the
arithmetic mean $0.6$.

### 20.5 Matrix factorization (`MatrixFactorizationRecommender._fit`)
Observed symmetric outcome matrix $R \in \mathbb{R}^{n\times n}$ with NaN for unobserved pairs.
1. Global mean over observed entries: $\mu = \operatorname{mean}\{R_{ij} : R_{ij}\neq \text{NaN}\}$.
2. Impute + mean-center: $\tilde{R} = R_{\text{filled}} - \mu$ (missing entries set to $\mu$, so
   centered to 0).
3. Truncated SVD with rank $f$ (latent factors): $\tilde{R} = U\Sigma V^{\top}$, keep top $f$
   singular triplets:
   $$ \hat{R} = U_{:,1:f}\,\Sigma_{1:f}\,V_{:,1:f}^{\top} + \mu. $$
4. Rank candidates for user $i$ by the reconstructed row $\hat{R}_{i,\cdot}$ (descending), excluding
   self and current team members. Users absent at fit time have no row $\Rightarrow$ cold-start
   $\Rightarrow$ `HybridRecommender` falls back to the content ranker.

Truncated SVD is the optimal rank-$f$ approximation in Frobenius norm (Eckart–Young), so it denoises
the sparse outcome matrix and fills unseen pairs with the dominant latent structure (including the
hidden "popularity" factor the content model cannot observe).

### 20.6 Ranking metrics
For a ranked id list and graded relevance $\mathrm{rel}_p$ at position $p$:
$$ \mathrm{DCG}@k = \sum_{p=1}^{k} \frac{\mathrm{rel}_p}{\log_2(p+1)}, \qquad
   \mathrm{NDCG}@k = \frac{\mathrm{DCG}@k}{\mathrm{IDCG}@k}, $$
where $\mathrm{IDCG}@k$ is $\mathrm{DCG}@k$ under the ideal (relevance-sorted) ordering.
Hit-rate@k $= \mathbb{1}[\,\text{any relevant id in top-}k\,]$. Coverage $=$ (distinct ids ever
recommended) $/$ (catalog size) — the diversity / popularity-bias gauge.

### 20.7 Expected Calibration Error (calibration evidence)
Partition predictions into $B$ equal-width confidence bins $\{B_b\}$. With $N$ total predictions,
$\mathrm{acc}(B_b)$ the empirical accuracy and $\mathrm{conf}(B_b)$ the mean predicted confidence in
bin $b$:
$$ \mathrm{ECE} = \sum_{b=1}^{B} \frac{|B_b|}{N}\,\bigl|\,\mathrm{acc}(B_b) - \mathrm{conf}(B_b)\,\bigr|. $$
A perfectly calibrated model has $\mathrm{acc}(B_b)=\mathrm{conf}(B_b)$ in every bin $\Rightarrow$
ECE $=0$ and the reliability curve lies on the diagonal. Measured: naive $0.3748 \to$ Platt $0.0099$.

> The 3PL item-characteristic curve, Fisher information $I(\theta)=\frac{a^2(P-c)^2}{(1-c)^2 P(1-P)}$,
> EAP $\hat\theta$, and Platt logistic $\sigma(Az+B)$ are derived in `INTERVIEW_PREP.md` Parts 6–8.
