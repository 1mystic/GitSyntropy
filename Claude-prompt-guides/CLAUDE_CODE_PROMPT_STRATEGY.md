# GitSyntropy: Claude Code Development Strategy
## Prompt Framework for Complete Backend & Frontend Build

**Purpose:** Enable Claude Code to understand the entire GitSyntropy project architecture, assess current scaffolding state, and iteratively build out all remaining features, APIs, agents, and frontend components to production-ready status.

**Target Outcome:** Feature-complete, deployment-ready GitSyntropy with all backend services, agentic orchestration, and frontend interfaces fully functional.

---

## SECTION 1: CONTEXT-SETTING MASTER PROMPT

Use this as your **first interaction** with Claude Code. It establishes the entire project context, vision, and technical stack.

### MASTER PROMPT (Copy-Paste into Claude Code)

```
You are now architecting and building GitSyntropy, an AI-native team composition intelligence platform. 
This is the most important context you'll have — read carefully and ask clarifying questions if needed.

═══════════════════════════════════════════════════════════════════════════════════════════════════════

PROJECT VISION:
GitSyntropy is a multi-agent orchestration system that analyzes GitHub teams using:
1. **Vedic Ashtakoot Framework**: 8 weighted dimensions of team compatibility (36 total points)
   - Nadi (8pts): Chronotype Sync — peak work hour overlap
   - Bhakoot (7pts): Stress Response Alignment
   - Gana (6pts): Risk Tolerance — bold vs cautious
   - Graha Maitri (5pts): Decision Framework — data-driven vs intuitive
   - Yoni (4pts): Conflict Resolution Style
   - Maitri (3pts): Social Compatibility
   - Vashya (2pts): Leadership Orientation
   - Varna (1pts): Innovation Drive

2. **Behavioral Signals**: GitHub commit history (90-day), chronotype detection, collaboration patterns
3. **Psychometric Assessment**: 8-question adaptive CAT quiz (5 minutes)
4. **Agentic Orchestration**: Multi-agent DAG with 4 specialized agents
5. **Streaming Synthesis**: Claude API generates narrative recommendations, meeting times, hiring suggestions

COMPATIBILITY SCORING:
- Score > 28: Excellent compatibility
- Score 18-28: Moderate, needs monitoring
- Score < 18: High friction risk

═══════════════════════════════════════════════════════════════════════════════════════════════════════

TECHNICAL STACK:
Backend:
  - FastAPI 0.115+ (async, REST + WebSocket)
  - LangGraph (multi-agent orchestration, state DAG)
  - Claude API (synthesis agent, streaming)
  - PyGithub + gql (GitHub GraphQL client)
  - Supabase PostgreSQL + pgvector (data persistence, RLS)
  - Python 3.11+, pytest, UV package manager

Frontend:
  - Astro 4.x (zero-JS by default, React islands)
  - React 18 (interactive islands only)
  - TypeScript
  - Tailwind CSS
  - Recharts (Ashtakoot radar, score timeline)
  - D3.js (chronotype heatmap)
  - Vercel deployment

Infrastructure:
  - Railway.app for FastAPI (GitHub Student Pack — no sleep)
  - Vercel for Astro frontend
  - GitHub Actions (lint, test, deploy)
  - Sentry for error tracking

═══════════════════════════════════════════════════════════════════════════════════════════════════════

FOUR CORE AGENTS (LangGraph):
1. **GitHub Analyst Agent**
   - Extracts 90-day commit history via GraphQL
   - Detects chronotype (K-Means clustering on timestamps)
   - Calculates collaboration metrics (PR response time, review frequency)
   - Stores raw signals in Supabase

2. **Psychometric Agent**
   - Administers 8-question adaptive assessment
   - Scores all 8 Ashtakoot dimensions
   - Implements CAT (Computerized Adaptive Testing) logic
   - Persists profile to Supabase

3. **Compatibility Engine Agent**
   - Computes variance-weighted pairwise scores
   - Generates team-level Ashtakoot matrix
   - Performs Monte Carlo simulation (1000 iterations) for candidate hiring
   - Detects risk flags (critical dimension misalignment)

4. **Synthesis Agent** (Claude API)
   - Ingests all upstream agent outputs
   - Generates narrative team health report
   - Recommends optimal meeting times (from chronotype heatmap)
   - Suggests candidate profiles to hire for gap-filling
   - Flags early warning signals
   - Streams response character-by-character to frontend

═══════════════════════════════════════════════════════════════════════════════════════════════════════

YOUR TASKS:
1. **Understand current project state** 
   - Look at the directory structure first
   - Identify what's scaffolded, what's partial, what's missing
   - Report findings before suggesting changes

2. **Build iteratively by feature**
   - Feature 1: GitHub OAuth + user authentication
   - Feature 2: GitHub Analyst Agent (complete pipeline)
   - Feature 3: Psychometric Agent + assessment UI
   - Feature 4: Compatibility Engine Agent + scoring
   - Feature 5: LangGraph Orchestration + WebSocket streaming
   - Feature 6: Claude Synthesis Agent + recommendations
   - Feature 7: Frontend Dashboard (radar chart, heatmap, timeline)
   - Feature 8: Team management UX (create, invite, manage)
   - Feature 9: Error handling, rate limiting, performance
   - Feature 10: Testing, documentation, deployment config

3. **For each feature, deliver:**
   - Complete working code (no TODOs)
   - Unit tests (pytest for backend, minimal coverage thresholds)
   - Updated database schema migrations (if needed)
   - Frontend components (if UI required)
   - API documentation (docstrings, OpenAPI schema)

4. **Quality standards:**
   - All endpoints have proper error handling (try/except, validation)
   - Async/await throughout (no blocking I/O)
   - Type hints on all functions (Python: mypy compatible)
   - Environment variables for secrets (no hardcoding API keys)
   - Graceful degradation (partial scores if data missing)
   - P95 latency < 10s for full team analysis

═══════════════════════════════════════════════════════════════════════════════════════════════════════

NEXT STEPS:
1. Ask me to @project-root or provide the directory so you can run:
   - `ls -la` to see structure
   - `find . -name "*.py" -o -name "*.ts" -o -name "*.tsx" | head -50` to see existing code
   - `cat requirements.txt` (or UV pyproject.toml) to see dependencies
   - `cat package.json` to see frontend setup

2. After reading the codebase, report back with:
   - Current completion percentage (e.g., "30% of backend scaffolded, 10% of frontend")
   - List of completed features (what works end-to-end)
   - List of partial features (what's started but incomplete)
   - List of missing features (what hasn't been touched)
   - Recommended build order (in what sequence should we complete features)

3. We'll then tackle features one at a time, with you taking full ownership of:
   - Writing production-ready code
   - Running tests
   - Deploying to staging (Railway/Vercel) if needed
   - Asking clarifying questions if requirements are ambiguous

═══════════════════════════════════════════════════════════════════════════════════════════════════════

START HERE:
Please tell me the path to your project root directory. I will:
1. Explore the scaffolding
2. Understand what's implemented
3. Ask clarifying questions about any ambiguous requirements
4. Propose a detailed execution plan with concrete milestones
5. Build the first feature end-to-end as a reference implementation

Ready? Give me the project path.
```

---

## SECTION 2: PROJECT ASSESSMENT PROMPT

After Claude Code explores your project, use this prompt to get a comprehensive status report.

### ASSESSMENT PROMPT (After Claude reads the directory)

```
@project-root

Now that you've seen the project structure, generate a comprehensive assessment:

1. **COMPLETION STATUS**
   - Overall completion %
   - Backend %: (scaffold/core logic/agents/testing/deployment)
   - Frontend %: (scaffold/pages/components/integrations/testing)

2. **SCAFFOLDING INVENTORY**
   For each item, state: ✓ Complete | ◐ Partial | ✗ Missing
   
   **Backend:**
   - [ ] FastAPI app initialization (main.py, settings, logging)
   - [ ] Database models (SQLAlchemy or similar)
   - [ ] Supabase schema & migrations
   - [ ] GitHub OAuth flow (login, token refresh)
   - [ ] JWT token generation & validation
   - [ ] GitHub GraphQL client setup
   - [ ] GitHub Analyst Agent (code structure exists?)
   - [ ] Psychometric Agent (code structure exists?)
   - [ ] Compatibility Engine Agent (code structure exists?)
   - [ ] LangGraph orchestrator (state schema, agent DAG)
   - [ ] WebSocket endpoint for streaming
   - [ ] Claude API client
   - [ ] Synthesis Agent (code structure exists?)
   - [ ] Background task runner (for GitHub sync)
   - [ ] API rate limiting middleware
   - [ ] Error handling & logging
   - [ ] Test suite structure
   - [ ] Deployment config (Railway)

   **Frontend:**
   - [ ] Astro 4.x project setup
   - [ ] React islands configured
   - [ ] Tailwind CSS setup
   - [ ] TypeScript configured
   - [ ] Authentication flow (login page)
   - [ ] Dashboard page (layout)
   - [ ] Team overview component
   - [ ] Ashtakoot radar chart (recharts)
   - [ ] Chronotype heatmap (D3)
   - [ ] Score history timeline (recharts)
   - [ ] Agent stream view (WebSocket consumer)
   - [ ] Team creation form
   - [ ] Assessment form component
   - [ ] Responsive design (mobile/tablet)
   - [ ] Test suite structure
   - [ ] Deployment config (Vercel)

3. **CRITICAL GAPS** (What's missing that blocks other features?)
   For example: "No Supabase schema → can't test GitHub Analyst Agent"

4. **READY-TO-BUILD CHECKLIST** (What's the first feature with all dependencies satisfied?)

5. **RECOMMENDED BUILD ORDER**
   "I recommend building in this order because..."
   List 8-10 features in order, with dependencies noted.

6. **BLOCKERS OR AMBIGUITIES**
   "I need clarification on:
   - [Question about requirement]
   - [Question about design]"

Then wait for my instructions on the first feature to build.
```

---

## SECTION 3: FEATURE-BY-FEATURE BUILD PROMPTS

Once you have the assessment, use these templated prompts to build each feature iteratively.

### TEMPLATE: BUILD FEATURE X

```
BUILD FEATURE: [Feature Name]

REQUIREMENTS:
[Copy-paste the relevant section from the architecture doc]

ACCEPTANCE CRITERIA:
- [ ] Code is production-ready (no TODOs, all edge cases handled)
- [ ] All functions have type hints and docstrings
- [ ] Unit tests pass (pytest for backend, 100% coverage on business logic)
- [ ] Database migrations run cleanly (if needed)
- [ ] Error handling includes proper logging
- [ ] Environment variables documented
- [ ] README updated with new endpoint/component docs
- [ ] Integrates cleanly with existing code (no refactoring required)

DELIVERABLES:
1. Complete backend code (if applicable)
   - New files or modifications to existing files
   - All imports, dependencies, edge cases handled
   - Ready to run without further changes
   
2. Frontend code (if applicable)
   - New components or pages
   - Properly typed, fully functional
   - Responsive design included
   
3. Tests
   - Minimal 80% coverage on new code
   - Edge case tests (error scenarios, boundary conditions)
   
4. Database changes (if applicable)
   - SQL migration file (created at specific timestamp)
   - Models updated
   
5. Documentation
   - API docstrings (if new endpoint)
   - Component prop types (if React component)
   - Environment variables needed (in .env.example)

CONSTRAINTS:
- Use async/await for all I/O (no blocking calls)
- Type hints required (mypy --strict compatible)
- No dependencies not already in requirements.txt
- Keep functions under 50 lines (complex logic → separate functions)
- Graceful error handling (user sees friendly message, logs have details)

BUILD THIS NOW. When done, run:
1. (Backend) pytest [new_test_file.py] -v
2. (Frontend) Check rendering in browser if component

Then report: "FEATURE [Name] COMPLETE" with summary of what was built.
```

---

## SECTION 4: SPECIFIC FEATURE PROMPTS

Build these features in order. Copy the relevant prompt for each feature.

### FEATURE 1: GitHub OAuth & User Authentication

```
BUILD FEATURE: GitHub OAuth & User Authentication

CONTEXT:
Users must authenticate via GitHub OAuth to access the app. This is the foundation for all other features.

REQUIREMENTS FROM ARCHITECTURE:
- GitHub OAuth flow (FastAPI backend)
- JWT token generation and validation
- Supabase user table (user_id, github_username, github_id, email, created_at, last_login)
- @user dependency for protected endpoints
- Frontend login page with "Sign in with GitHub" button
- Login redirect → /dashboard after successful auth

ARCHITECTURE DETAILS:
- Use github.com OAuth app (user will create credentials)
- FastAPI endpoints:
  - POST /auth/github (receives code from frontend)
  - POST /auth/refresh (refresh JWT token)
  - GET /auth/me (returns current user, requires JWT)
  - POST /auth/logout (invalidates token)
- Frontend:
  - Login page (landing page for unauthenticated)
  - Redirect to GitHub OAuth
  - Handle callback with code param
  - Store JWT in httpOnly cookie
  - Protected routes check JWT

DATABASE SCHEMA:
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  github_username TEXT UNIQUE NOT NULL,
  github_id INT UNIQUE NOT NULL,
  email TEXT UNIQUE,
  avatar_url TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  last_login TIMESTAMP,
  updated_at TIMESTAMP DEFAULT NOW()
);

DELIVERABLES:
1. Backend:
   - app/auth.py (OAuth flow, JWT logic)
   - app/dependencies.py (get_current_user decorator)
   - app/routes/auth.py (4 endpoints above)
   - app/models/user.py (SQLAlchemy User model)
   - Migration: 001_create_users_table.sql

2. Frontend:
   - src/pages/login.astro (landing + login button)
   - src/pages/auth/callback.astro (handles OAuth callback)
   - src/components/ProtectedRoute.tsx (wrapper for protected pages)
   - src/utils/auth.ts (JWT storage/retrieval, fetch helper with auth)

3. Tests:
   - tests/test_auth.py (OAuth flow, token refresh, protected endpoints)

4. Environment:
   - GITHUB_CLIENT_ID
   - GITHUB_CLIENT_SECRET
   - JWT_SECRET_KEY
   - FRONTEND_URL

CONSTRAINTS:
- Use PyJWT library (already common in FastAPI projects)
- httpOnly cookies for JWT (prevent XSS theft)
- CSRF token for logout
- User created in Supabase on first OAuth (upsert logic)

GO. Build this feature end-to-end. When done, report what you've built and any questions.
```

### FEATURE 2: GitHub Analyst Agent

```
BUILD FEATURE: GitHub Analyst Agent

CONTEXT:
This agent extracts behavioral signals from GitHub commit history (90 days):
- Commit timestamp patterns (chronotype detection via K-Means)
- Collaboration metrics (PR response time, review frequency)
- Contribution frequency
The goal: objective signals that feed into Ashtakoot scoring.

REQUIREMENTS FROM ARCHITECTURE:
"GitHub GraphQL client (PyGithub + gql)
Commit timestamp extraction (90-day history)
Chronotype detection algorithm (K-Means implementation)
Collaboration metrics extraction (PR response time, review patterns)
Background task: GitHub sync via FastAPI BackgroundTasks
Sync status polling endpoint"

CHRONOTYPE DETECTION ALGORITHM:
Input: List of commit timestamps over 90 days
Process:
  1. Extract hour-of-day for each commit
  2. Run K-Means with k=3 clusters (early bird, mid-day, night owl)
  3. Find cluster with highest density → person's "peak time"
  4. Calculate hours_active_per_day (average commits by hour)
  5. Output: peak_hour (0-23), peak_hours_list (sorted by activity)
Example: Person commits mostly 9-11 AM → peak_hour = 10

DATABASE SCHEMA:
CREATE TABLE github_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  github_username TEXT NOT NULL,
  github_id INT NOT NULL,
  last_synced_at TIMESTAMP,
  synced_successfully BOOLEAN,
  
  -- Behavioral signals
  commits_90d INT,
  peak_hour INT (0-23),
  peak_hours_list INT[] (e.g., [9, 10, 11]),
  hours_active_per_day FLOAT,
  
  -- Collaboration metrics
  avg_pr_response_time_hours FLOAT,
  review_frequency_per_week FLOAT,
  pr_comment_frequency FLOAT,
  
  -- Raw data (for agent audit)
  raw_commit_data JSONB,
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE github_sync_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  github_username TEXT NOT NULL,
  status TEXT ('pending', 'success', 'failed'),
  error_message TEXT,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  commits_extracted INT
);

DELIVERABLES:
1. Backend:
   - app/agents/github_analyst.py
     * class GitHubAnalystAgent:
       - async extract_commit_history(username, days=90)
       - detect_chronotype(commit_timestamps) → (peak_hour, peak_hours_list, hours_active)
       - extract_collaboration_metrics(username) → (avg_response_time, review_freq)
       - async run(user_id, github_username) → saves to DB

   - app/routes/github.py
     * POST /github/sync (start background sync)
     * GET /github/sync-status/{user_id} (poll status)
     * GET /github/profile/{user_id} (retrieve profile)

   - app/clients/github_graphql.py
     * class GitHubGraphQLClient:
       - async get_commits(username, days=90)
       - async get_prs_and_reviews(username)
       - async get_user_info(username)

2. Tests:
   - tests/test_github_analyst.py
     * Test K-Means chronotype detection with mock timestamps
     * Test collaboration metrics extraction
     * Test edge cases (user with no commits, user with no reviews)

3. Environment:
   - GITHUB_TOKEN (personal access token, for API auth)
   - GITHUB_GRAPHQL_ENDPOINT (should be https://api.github.com/graphql)

4. Documentation:
   - Explain chronotype algorithm in docstring
   - Document what each metric means

CONSTRAINTS:
- GitHub API rate limits: 5000 points/hour (check headers, implement backoff)
- Only fetch 90 days of history (pagination, cursor-based)
- Async throughout (no blocking GitHub calls)
- Handle case where user has no public activity
- Graceful fallback if GitHub API fails

GO. Build this feature. Report when done.
```

### FEATURE 3: Psychometric Agent & Assessment

```
BUILD FEATURE: Psychometric Agent & Assessment UI

CONTEXT:
Users take an 8-question adaptive psychometric quiz (CAT: Computerized Adaptive Testing).
Each question maps to one Ashtakoot dimension. Scores feed into compatibility engine.

REQUIREMENTS FROM ARCHITECTURE:
"8-question assessment API (submit + retrieve)
Score computation for all 8 Ashtakoot dimensions
Adaptive question ordering (CAT: harder questions if initial answers suggest extreme scores)
Profile storage in Supabase
Frontend: Assessment form component (Astro page + React island)"

ASHTAKOOT DIMENSION → QUESTION MAPPING:
1. Nadi (Chronotype Sync, 8pts): "Are you most productive in the morning?" (early bird vs night owl)
2. Bhakoot (Stress Response, 7pts): "How do you typically handle project pressure?" (calm vs reactive)
3. Gana (Risk Tolerance, 6pts): "When uncertain, do you prefer to move fast or gather data?" (bold vs cautious)
4. Graha Maitri (Decision Framework, 5pts): "Are decisions best made with data or intuition?" (analytical vs intuitive)
5. Yoni (Conflict Resolution, 4pts): "In disagreements, do you prefer to address directly or find compromise?" (direct vs avoidant)
6. Maitri (Communication, 3pts): "Do you prefer synchronous or asynchronous communication?" (sync vs async)
7. Vashya (Leadership, 2pts): "Do you prefer to lead or be led?" (directive vs collaborative)
8. Varna (Innovation, 1pts): "Do you favor proven practices or experimental approaches?" (incremental vs disruptive)

SCORING SYSTEM:
- Each question: Likert scale 1-5 (Strongly Disagree to Strongly Agree)
- Raw score for dimension = respondent's answer (1-5)
- Scaled score for dimension = (raw_score / 5) * dimension_points
  Example: Nadi question answered "4" → (4/5) * 8 = 6.4 points
- Total team score = sum of all 8 scaled scores (max 36)

CAT (ADAPTIVE TESTING):
- Initial 4 questions presented in sequence
- After Q4, calculate preliminary scores for those 4 dimensions
- If any dimension score is < 2 or > 4 (extreme), present next harder/easier variant of that dimension's question
- For balanced responses, present standard remaining questions
- Total: 8 questions max, adaptive based on response pattern

DATABASE SCHEMA:
CREATE TABLE psychometric_assessments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) UNIQUE,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  status TEXT ('in_progress', 'completed'),
  
  -- Raw responses (one row per question)
  responses JSONB (array of {dimension, answer: 1-5, question_order}),
  
  -- Computed scores
  nadi_score FLOAT (0-8),
  bhakoot_score FLOAT (0-7),
  gana_score FLOAT (0-6),
  graha_maitri_score FLOAT (0-5),
  yoni_score FLOAT (0-4),
  maitri_score FLOAT (0-3),
  vashya_score FLOAT (0-2),
  varna_score FLOAT (0-1),
  total_score FLOAT (0-36),
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

DELIVERABLES:
1. Backend:
   - app/agents/psychometric_agent.py
     * class PsychometricAgent:
       - get_questions() → list[{id, dimension, text, order}]
       - submit_answer(user_id, question_id, answer: 1-5) → {next_question_id or null}
       - compute_scores(user_id) → {nadi, bhakoot, ..., total}
       - get_assessment(user_id) → full assessment with scores

   - app/routes/psychometric.py
     * POST /psychometric/start (create assessment, return first question)
     * POST /psychometric/answer (submit answer, get next question)
     * GET /psychometric/assessment/{user_id} (retrieve completed assessment)

2. Frontend:
   - src/pages/assessment.astro (assessment page layout)
   - src/components/AssessmentForm.tsx (React island)
     * Display question
     * Likert scale (1-5 radio buttons or slider)
     * Progress indicator (Q3/8)
     * Submit button
     * On completion: show scores (radar chart or summary)

3. Tests:
   - tests/test_psychometric.py
     * Test score computation for all dimensions
     * Test CAT logic (if answer extreme, next question is harder)
     * Test edge cases (user answers all 1s, all 5s)

4. Environment: None new

CONSTRAINTS:
- All 8 questions must be non-trivial (Likert scale, not yes/no)
- CAT algorithm must be deterministic (same responses → same question sequence)
- Scores persist after completion (user can review)
- Assessment expires after 6 months (optional: require retake)

GO. Build this feature. Report when done.
```

### FEATURE 4: Compatibility Engine Agent

```
BUILD FEATURE: Compatibility Engine Agent

CONTEXT:
This agent ingests GitHub signals + psychometric profiles and computes:
- Pairwise Ashtakoot compatibility scores for each pair in a team
- Team-level aggregate score
- Risk flags (critical misalignments)
- Monte Carlo simulation for candidate hiring

REQUIREMENTS FROM ARCHITECTURE:
"Variance-weighted Ashtakoot scoring (all 8 dimensions)
Pairwise score matrix for team members
Risk flag detection (critical misalignment conditions)
Monte Carlo candidate simulation (1000 iterations)"

SCORING ALGORITHM:
For each pair (member_A, member_B):
  For each dimension d in [nadi, bhakoot, gana, ...]:
    delta_d = abs(member_A.score_d - member_B.score_d)
    compatibility_d = dimension_points * (1 - delta_d / 5)  // normalize by 5 (max scale)
    weighted_score_d = compatibility_d * dimension_weight
  
  total_pairwise_score = sum(weighted_scores)

Team score = average of all pairwise scores

Example:
- Member A: nadi=6, bhakoot=5, gana=4, ...
- Member B: nadi=4, bhakoot=5, gana=4, ...
- Nadi delta = |6-4| = 2
- Nadi compatibility = 8 * (1 - 2/5) = 8 * 0.6 = 4.8
- Nadi weighted = 4.8 * 1.0 (no dimension weight, just points)
- ... repeat for all 8 dimensions, sum

RISK FLAGS:
- Critical misalignment: any dimension delta > 3 → flag "Schedule conflict risk" (chronotype)
- Stress response mismatch: bhakoot delta > 2 → flag "Pressure handling mismatch"
- Decision style clash: graha_maitri + yoni delta > 3 → flag "Collaboration friction"

DATABASE SCHEMA:
CREATE TABLE team_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID NOT NULL REFERENCES teams(id),
  
  -- Pairwise matrix (JSONB)
  pairwise_scores JSONB (
    {
      "member_a_member_b": 28.5,
      "member_a_member_c": 22.3,
      ...
    }
  ),
  
  -- Team aggregate
  team_score FLOAT (0-36),
  score_variance FLOAT,
  
  -- Risk flags
  risk_flags JSONB (
    [
      {dimension: "nadi", members: ["alice", "bob"], severity: "high"},
      ...
    ]
  ),
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE team_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID NOT NULL REFERENCES teams(id),
  user_id UUID NOT NULL REFERENCES users(id),
  joined_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(team_id, user_id)
);

DELIVERABLES:
1. Backend:
   - app/agents/compatibility_engine.py
     * class CompatibilityEngineAgent:
       - compute_pairwise_score(profile_a, profile_b) → float (0-36)
       - compute_team_score(team_id) → (total_score, pairwise_matrix, variance)
       - detect_risk_flags(team_id) → list[RiskFlag]
       - simulate_candidate_hire(team_id, candidate_profile, iterations=1000) → (new_score, confidence_interval)

   - app/routes/compatibility.py
     * POST /teams/{team_id}/analyze (compute all scores)
     * GET /teams/{team_id}/score (retrieve latest score)
     * GET /teams/{team_id}/risks (list risk flags)
     * POST /teams/{team_id}/simulate-hire (post candidate profile, get simulation)

2. Models:
   - app/models/team.py (Team, TeamMember, TeamScore models)

3. Tests:
   - tests/test_compatibility_engine.py
     * Test pairwise score computation (known pairs, expected scores)
     * Test risk flag detection
     * Test Monte Carlo sim (results should be normally distributed)
     * Test edge cases (identical profiles, opposite profiles)

4. Environment: None new

CONSTRAINTS:
- Pairwise scoring is O(n²), cache results for teams > 20 members
- Monte Carlo uses Gaussian perturbation (std_dev = 0.5 for profile scores)
- Risk flags must be deterministic (same inputs → same flags)
- Simulate hire should not mutate team, only return prediction

GO. Build this feature. Report when done.
```

### FEATURE 5: LangGraph Orchestration & WebSocket Streaming

```
BUILD FEATURE: LangGraph Orchestration & WebSocket Streaming

CONTEXT:
LangGraph coordinates all 4 agents (GitHub, Psychometric, Compatibility, Synthesis).
User initiates team analysis → orchestrator builds agent DAG → each agent runs, intermediate results stream to frontend via WebSocket.

REQUIREMENTS FROM ARCHITECTURE:
"LangGraph state schema definition
Agent DAG construction (all 4 agents + conditional routing)
WebSocket endpoint for streaming agent events
Agent audit log (agent_runs table)"

LANGGRAPH STATE SCHEMA:
@dataclass
class TeamAnalysisState:
  team_id: str
  team_members: list[TeamMember]
  
  # Intermediate results from each agent
  github_data: dict  # {member: {peak_hour, commits_90d, ...}}
  psychometric_data: dict  # {member: {nadi, bhakoot, ...}}
  compatibility_scores: dict  # {pairwise_matrix, team_score, risks}
  synthesis_report: str  # Claude's narrative
  
  # Metadata
  started_at: datetime
  current_stage: str  # "github" | "psychometric" | "compatibility" | "synthesis" | "complete"
  errors: list[str]

AGENT DAG:
Start
  ├─ GitHub Analyst (sync all members' data in parallel)
  │  └─ update state.github_data
  │     └─ stream: "GitHub Analyst: Extracted 90-day history for [member]"
  │
  ├─ Psychometric Agent (retrieve profiles, compute scores)
  │  └─ update state.psychometric_data
  │     └─ stream: "Psychometric Agent: Profiles loaded, computed dimension scores"
  │
  ├─ Compatibility Engine (compute team scores + risks)
  │  └─ update state.compatibility_scores
  │     └─ stream: "Compatibility Engine: Team score = 28.5, detected 2 risk flags"
  │
  └─ Synthesis Agent (Claude, generate narrative)
     └─ update state.synthesis_report (stream token-by-token)
        └─ stream: "Synthesis Agent: [narrative text as it streams]"
End

DATABASE SCHEMA:
CREATE TABLE agent_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID NOT NULL REFERENCES teams(id),
  run_started_at TIMESTAMP DEFAULT NOW(),
  run_completed_at TIMESTAMP,
  
  -- State snapshots
  initial_state JSONB,
  final_state JSONB,
  
  -- Execution log
  execution_log JSONB (
    [
      {agent: "github", started_at, completed_at, status, result_summary},
      {agent: "psychometric", ...},
      ...
    ]
  ),
  
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agent_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES agent_runs(id),
  agent_name TEXT,
  event_type TEXT ('started', 'completed', 'error', 'intermediate'),
  message TEXT,
  data JSONB,
  timestamp TIMESTAMP DEFAULT NOW()
);

DELIVERABLES:
1. Backend:
   - app/orchestration/state.py
     * Define TeamAnalysisState dataclass

   - app/orchestration/graph.py
     * class TeamAnalysisOrchestrator:
       - build_graph() → LangGraph StateGraph
       - async run(team_id) → yields (state, event) tuples
       - Methods for each agent node:
         * node_github_analyst(state) → updated_state
         * node_psychometric(state) → updated_state
         * node_compatibility(state) → updated_state
         * node_synthesis(state) → updated_state

   - app/routes/teams.py
     * POST /teams/{team_id}/analyze (start analysis, return run_id)
     * WebSocket /ws/team-analysis/{run_id} (stream events)

   - app/websocket_manager.py
     * class WebSocketManager:
       - async stream_agent_events(run_id, ws) → streams events as they happen

2. Integration:
   - Modify GitHub Analyst, Psychometric, Compatibility agents to emit events
   - Each agent: log to agent_events table on completion

3. Tests:
   - tests/test_orchestration.py
     * Test DAG construction (correct node order)
     * Test state propagation (initial state → final state)
     * Test error handling (if one agent fails, orchestration stops)

4. Environment: None new

CONSTRAINTS:
- All agent calls must be async
- State updates must be immutable (functional style)
- WebSocket only sends diff, not full state (reduce payload)
- Audit log captures both input and output of each agent

GO. Build this feature. Report when done.
```

### FEATURE 6: Claude Synthesis Agent & Recommendations

```
BUILD FEATURE: Claude Synthesis Agent & Recommendations

CONTEXT:
Claude API ingests orchestrator state (GitHub data, psychometric scores, compatibility analysis).
Claude generates narrative team health report, meeting time recommendations, hiring gap suggestions.
Response streams token-by-token to frontend (impressive UX).

REQUIREMENTS FROM ARCHITECTURE:
"Synthesis agent: Claude API with structured context injection
Streaming response → WebSocket → frontend
Meeting window recommendations (chronotype-based)
Hiring gap analysis (which dimension is weakest, what profile fills it)"

SYNTHESIS PROMPT (System):
You are a team dynamics expert analyzing a software engineering team using the Vedic Ashtakoot compatibility framework.

You have been given:
1. GitHub behavioral data: commit patterns, chronotype, collaboration metrics
2. Psychometric profiles: 8 Ashtakoot dimension scores for each member
3. Compatibility analysis: pairwise scores, team aggregate score, detected risk flags

Your task:
1. Generate a 2-3 paragraph narrative team health report:
   - Interpret the compatibility score (is the team well-aligned?)
   - Highlight key strengths (high-alignment dimensions)
   - Identify friction points (low-alignment dimensions, risk flags)
   - Tone: professional, data-driven, not alarmist

2. Recommend optimal meeting times:
   - Analyze chronotype data (peak hours for each member)
   - Find 2-3 time windows where majority of team is peak-productive
   - Format: "Tuesday & Thursday, 10 AM - 11 AM EST works for [X/Y] team members"

3. Suggest hiring to strengthen the team:
   - Identify weakest dimension (lowest average score)
   - Recommend profile for new hire (what scores would complement the team)
   - Format: "Hire someone with high [dimension] to balance the team's [weakness]"

4. Flag early warnings:
   - If team score < 20: "Critical: Immediate intervention needed"
   - If 2+ risk flags: "Monitor: Schedule 1-on-1s with flagged pairs"
   - If member has isolated dimension: "Consider cross-training in [area]"

Keep output concise (under 500 words). Be specific with data.

DELIVERABLES:
1. Backend:
   - app/agents/synthesis_agent.py
     * class SynthesisAgent:
       - async synthesize(state: TeamAnalysisState) → AsyncGenerator[str, None]
         (yields chunks of Claude's response)
       - prepare_context(state) → formatted_string
         (structures state into clean prompt context)
       - extract_recommendations(response: str) → {health_report, meeting_times, hiring_gaps, warnings}
         (optional: parse structured output from Claude)

   - Modify app/orchestration/graph.py:
     * node_synthesis(state) → integrates SynthesisAgent
     * Yields each token from Claude to WebSocket

2. Integration:
   - Environment: ANTHROPIC_API_KEY

3. Tests:
   - tests/test_synthesis_agent.py
     * Test synthesis with mock state
     * Verify output contains all 4 sections (report, meetings, hiring, warnings)
     * Test streaming (mock Claude API, verify generator yields chunks)

CONSTRAINTS:
- Use Claude API with streaming (stream=True)
- Respect rate limits (if needed, implement retry with backoff)
- Temperature = 0.7 (balance coherence + variety)
- Max tokens = 1000 (keep output focused)
- Handle API failures gracefully (return partial synthesis with disclaimer)

GO. Build this feature. Report when done.
```

### FEATURE 7: Frontend Dashboard

```
BUILD FEATURE: Frontend Dashboard & Visualizations

CONTEXT:
Users see team analysis results via interactive charts:
- Ashtakoot radar (8 dimensions, each member overlaid)
- Chronotype heatmap (24h × members, shows ideal meeting times)
- Score history timeline (team score over time as members join/leave)
- Agent stream view (live terminal feed of orchestration events)

REQUIREMENTS FROM ARCHITECTURE:
"Ashtakoot Radar Chart (React + recharts)
Chronotype Heatmap (React + D3)
Agent Stream View (React + WebSocket)
Score History Timeline (React + recharts)"

DELIVERABLES:
1. Frontend Components:
   - src/pages/dashboard.astro (main dashboard page)
   - src/components/AshtakootRadar.tsx (recharts radar chart)
     * Input: array of member profiles with 8 dimension scores
     * Output: overlaid radar for all members, color-coded
     * Tooltip: shows member name + dimension name + score on hover

   - src/components/ChronotypeHeatmap.tsx (D3 heatmap)
     * Input: members with peak_hours_list data
     * Output: 24-hour grid (x-axis) × members (y-axis)
     * Color intensity: activity density at each hour
     * Highlight ideal meeting windows (cells where 3+ members overlap)

   - src/components/AgentStreamView.tsx (WebSocket consumer)
     * Connect to /ws/team-analysis/{run_id}
     * Display messages in terminal-style feed (monospace font)
     * Auto-scroll to bottom
     * Color-code by agent (GitHub=blue, Psychometric=green, etc.)

   - src/components/ScoreHistoryTimeline.tsx (recharts line chart)
     * Input: team_score values with timestamps
     * Annotations: vertical dashed lines when member joined/left
     * Tooltip: shows score + member change on hover

   - src/components/TeamOverview.tsx (summary card)
     * Team name, member count
     * Current score (28/36)
     * Score interpretation (excellent / moderate / at-risk)
     * Last analysis date

2. Pages:
   - src/pages/dashboard.astro
     * Layout: sidebar (teams list) + main (dashboard)
     * Arrange components: overview + radar + heatmap + timeline
     * Add "Run Analysis" button

   - src/pages/teams/[id].astro
     * Individual team page
     * Include all 4 chart components
     * Show risk flags in red box
     * Show synthesis report below

3. Styling:
   - Responsive: mobile-first Tailwind
   - Dark mode support (optional, but nice)
   - Accessibility: proper ARIA labels on charts

4. Tests:
   - tests/components/ashtakoot_radar.test.ts
   - tests/components/chronotype_heatmap.test.ts
   - tests/components/agent_stream_view.test.ts

CONSTRAINTS:
- Use only recharts + D3, no extra charting libraries
- Charts must be responsive (resize with window)
- WebSocket connection must auto-reconnect on disconnect
- No external fonts (use system fonts or Tailwind defaults)

GO. Build this feature. Report when done.
```

### FEATURE 8: Team Management UX

```
BUILD FEATURE: Team Management UX (Create, Invite, Manage)

CONTEXT:
Users create teams, invite members, manage composition over time.
Invite link system: generate → share → accept → auto-join.
Member removal preview: show how team score changes if member removed.
Candidate simulator: add hypothetical member → see simulated impact.

REQUIREMENTS FROM ARCHITECTURE:
"Team creation flow
Invite link system (generate → share → accept → auto-join)
Member removal with score impact preview
Candidate simulator UI (add hypothetical member → see simulated score change)"

DELIVERABLES:
1. Backend:
   - app/routes/teams.py (expand from Feature 5)
     * POST /teams (create team)
     * GET /teams (list user's teams)
     * POST /teams/{team_id}/invite (generate invite link)
     * POST /teams/{team_id}/accept-invite/{token} (join team)
     * DELETE /teams/{team_id}/members/{user_id} (remove member)
     * POST /teams/{team_id}/simulate-member (preview adding/removing)

   - Database migrations:
     * CREATE TABLE teams (id, owner_id, name, created_at)
     * CREATE TABLE team_invites (id, team_id, token, expires_at, claimed_by)

2. Frontend:
   - src/pages/teams/new.astro (create team form)
     * Team name input
     * Optional: initial members list
     * Submit → POST /teams

   - src/components/InviteDialog.tsx
     * Displays invite link (copy to clipboard button)
     * QR code (optional, for mobile sharing)
     * Expiration time (24h default)

   - src/components/MemberRemovalPreview.tsx
     * Show member's contribution to team score
     * Preview: "If [member] leaves, team score drops from 28.5 → 24.2"
     * Confirm button

   - src/components/CandidateSim.tsx
     * Input form: candidate's psychometric scores (8 fields)
     * Button: "Simulate hiring"
     * Output: radar chart overlay (current team + new candidate)
     * Show predicted team score

3. Pages:
   - src/pages/teams/[id]/manage.astro
     * Member list with removal buttons
     * "Invite members" button → opens InviteDialog
     * "Simulate hire" button → opens CandidateSim

4. Tests:
   - tests/test_team_management.py
     * Test team creation
     * Test invite link generation + expiration
     * Test member removal + score recalculation

CONSTRAINTS:
- Invite tokens are random, 32 characters, URL-safe
- Tokens expire after 24 hours
- User cannot remove themselves (must transfer ownership first)
- Candidate sim is ephemeral (doesn't create team member)

GO. Build this feature. Report when done.
```

### FEATURE 9: Error Handling, Rate Limiting, Performance

```
BUILD FEATURE: Error Handling, Rate Limiting, Performance Optimization

CONTEXT:
Production-ready app must handle:
- GitHub API rate limits (5000 points/hour, implement backoff)
- User-friendly error messages (not raw 500 errors)
- Performance: P95 latency < 10s for team analysis
- Graceful degradation (partial scores if data missing)
- Comprehensive logging (Sentry for production)

DELIVERABLES:
1. Backend:
   - app/middleware/error_handler.py
     * Global exception handler (catches all unhandled exceptions)
     * Returns {error: "user-friendly message", code: "error_code", request_id: "uuid"}
     * Logs full error to Sentry

   - app/middleware/rate_limit.py
     * Rate limiting: 100 requests/minute per user
     * Return 429 with Retry-After header

   - app/clients/github_graphql.py (enhance)
     * Implement exponential backoff for rate limits
     * Cache responses (30 min TTL)
     * Graceful fallback if API fails

   - app/agents/* (enhance)
     * All agents: log start/end with duration
     * Add timing metrics (log which steps are slow)
     * Implement timeouts (abandon if taking > 30s)

   - app/routes/* (enhance)
     * Input validation (pydantic models, 400 on invalid)
     * Database transaction rollback on error
     * Partial response if some data missing (e.g., incomplete psychometric)

   - Performance profiling:
     * Add timing decorators to hot paths
     * Profile: "Team analysis took 8.2s (GitHub: 3s, Psychometric: 1s, Compatibility: 0.5s, Synthesis: 3.7s)"

2. Frontend:
   - src/utils/error.ts
     * Parse API error responses
     * Display user-friendly toast messages
     * Log to Sentry

   - src/components/* (enhance)
     * Add loading states (skeleton screens, not spinners)
     * Add error boundaries
     * Retry buttons for failed requests

3. Configuration:
   - .env.example (add Sentry DSN, rate limit config)
   - pyproject.toml (add sentry-sdk)

4. Tests:
   - tests/test_error_handling.py
     * Test rate limit enforcement
     * Test graceful degradation (partial profile → partial score)
     * Test timeout handling

CONSTRAINTS:
- Never expose internal error details to user (log, not display)
- All errors logged with request_id (traceable)
- Rate limiting key = user_id (not IP, to allow shared networks)
- Timeouts: 30s for agent execution, 10s for API calls

GO. Build this feature. Report when done.
```

### FEATURE 10: Testing, Documentation, Deployment Config

```
BUILD FEATURE: Testing, Documentation, Deployment Config

CONTEXT:
Final polish: comprehensive tests, clear documentation, ready-to-deploy configurations for Railway and Vercel.

DELIVERABLES:
1. Backend Testing:
   - tests/conftest.py
     * Fixtures: test_user, test_team, test_team_member
     * Mock GitHub API responses
     * Mock Claude API responses
     * Test database setup/teardown

   - tests/test_*.py (for each feature)
     * Unit tests (functions)
     * Integration tests (endpoints)
     * Minimal 80% coverage on business logic

   - pytest.ini
     * Configure pytest (addopts, testpaths)

   - Run: pytest --cov=app --cov-report=html (generates coverage report)

2. Frontend Testing (optional, minimal):
   - tests/components/*.test.ts
     * Test chart rendering with mock data
     * Test form submission

3. Documentation:
   - README.md
     * Problem statement
     * Solution overview
     * Architecture diagram (ASCII or Excalidraw PNG)
     * Quick start (clone, install, run locally)
     * Environment variables (with examples)
     * API documentation (link to /docs endpoint)
     * Contributing guidelines

   - docs/ARCHITECTURE.md (from uploaded file, adapt for code)
   - docs/API.md (auto-generated from FastAPI, or manual)
   - docs/AGENTS.md (explain each agent, its inputs/outputs)
   - docs/SCORING.md (detailed Ashtakoot algorithm explanation)

4. Deployment Config:
   - railway.toml
     * Service name, buildpack, start command
     * Environment variables (list of required vars)
     * Health check endpoint

   - vercel.json
     * Frontend deployment config
     * Rewrites for API proxy

   - docker-compose.yml (local dev)
     * FastAPI service
     * Supabase (or link to hosted instance)

   - GitHub Actions: .github/workflows/
     * ci.yml: lint + test on PR
     * deploy.yml: deploy on merge to main

5. Environment Files:
   - .env.example (copy and customize)
     * All required vars listed with placeholder values

CONSTRAINTS:
- Tests must pass before deployment
- All endpoints documented
- README should make setup obvious to newcomers
- Deployment automated (no manual steps)

GO. Build this feature. Report when done.
```

---

## SECTION 5: ITERATIVE BUILD CHECKLIST

Use this checklist to track progress as you build with Claude Code.

```
[ ] FEATURE 1: GitHub OAuth & User Authentication
    [ ] Backend: auth.py, dependencies.py, routes/auth.py, models/user.py
    [ ] Frontend: login.astro, auth/callback.astro, ProtectedRoute.tsx
    [ ] Tests: test_auth.py passes
    [ ] Database: users table created
    [ ] Environment: GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, JWT_SECRET_KEY configured

[ ] FEATURE 2: GitHub Analyst Agent
    [ ] Backend: agents/github_analyst.py, clients/github_graphql.py, routes/github.py
    [ ] Chronotype detection K-Means working
    [ ] Collaboration metrics extracted
    [ ] Database: github_profiles, github_sync_runs tables created
    [ ] Tests: test_github_analyst.py passes
    [ ] Environment: GITHUB_TOKEN configured

[ ] FEATURE 3: Psychometric Agent & Assessment
    [ ] Backend: agents/psychometric_agent.py, routes/psychometric.py
    [ ] 8 questions defined, CAT logic working
    [ ] Score computation for all dimensions
    [ ] Frontend: assessment.astro, AssessmentForm.tsx
    [ ] Database: psychometric_assessments table created
    [ ] Tests: test_psychometric.py passes

[ ] FEATURE 4: Compatibility Engine Agent
    [ ] Backend: agents/compatibility_engine.py, routes/compatibility.py
    [ ] Pairwise scoring algorithm working
    [ ] Team score aggregation working
    [ ] Risk flag detection working
    [ ] Monte Carlo simulation for candidates
    [ ] Database: team_scores, team_members tables created
    [ ] Tests: test_compatibility_engine.py passes

[ ] FEATURE 5: LangGraph Orchestration & WebSocket
    [ ] Backend: orchestration/state.py, orchestration/graph.py
    [ ] Agent DAG building correctly
    [ ] WebSocket endpoint streaming events
    [ ] Database: agent_runs, agent_events tables created
    [ ] Tests: test_orchestration.py passes

[ ] FEATURE 6: Claude Synthesis Agent
    [ ] Backend: agents/synthesis_agent.py
    [ ] Claude API integration working (streaming)
    [ ] Synthesis prompt tuned for good output
    [ ] All 4 recommendation types generated
    [ ] Tests: test_synthesis_agent.py passes
    [ ] Environment: ANTHROPIC_API_KEY configured

[ ] FEATURE 7: Frontend Dashboard
    [ ] Components: AshtakootRadar.tsx, ChronotypeHeatmap.tsx, AgentStreamView.tsx, ScoreHistoryTimeline.tsx
    [ ] Pages: dashboard.astro, teams/[id].astro
    [ ] Charts rendering correctly with mock data
    [ ] WebSocket connection working
    [ ] Responsive design tested

[ ] FEATURE 8: Team Management UX
    [ ] Backend: team CRUD endpoints, invite system, simulate endpoints
    [ ] Frontend: teams/new.astro, manage.astro, modals/dialogs
    [ ] Invite link generation + expiration working
    [ ] Member removal + score preview working
    [ ] Candidate simulator working
    [ ] Database: teams, team_invites tables created

[ ] FEATURE 9: Error Handling, Rate Limiting, Performance
    [ ] Global error handler working
    [ ] Rate limiting middleware active
    [ ] GitHub API backoff implemented
    [ ] Graceful degradation tested
    [ ] Loading states added to frontend
    [ ] Timing metrics logged

[ ] FEATURE 10: Testing, Documentation, Deployment
    [ ] pytest coverage > 80%
    [ ] README.md complete with architecture diagram
    [ ] API documentation generated
    [ ] Deployment configs (railway.toml, vercel.json, Dockerfile) ready
    [ ] GitHub Actions CI/CD configured
    [ ] .env.example populated

TOTAL PROGRESS: __/10 features complete
Estimated completion: [date]
```

---

## SECTION 6: COMMUNICATION PROTOCOL WITH CLAUDE CODE

After you give the master prompt, follow this protocol for smooth collaboration:

### For Each Feature:

1. **Initiate**: "BUILD FEATURE [X]: [Name]" (copy the template from Section 4)
2. **Claude explores**: Claude reads existing code, identifies what's done, what's missing
3. **Claude reports**: "I see [part A] is done, [part B] is partial, [part C] is missing. Here's the plan:"
4. **You confirm**: "Yes, proceed with [plan]" or "Also do [additional change]"
5. **Claude builds**: Code is written, tests run, report generated
6. **You review**: Read the code/tests, ask questions, request changes if needed
7. **You checkmark**: Mark feature as complete in the checklist

### Questions to Ask Claude:

- "Can you summarize what you've built in this feature?"
- "How does [new component] integrate with [existing component]?"
- "What's the test coverage percentage?"
- "Are there any known limitations or TODOs?"
- "How long will this feature take to build?"

### When Stuck:

- "I'm seeing error [X]. Can you debug?"
- "The requirement for [Y] is unclear. Should we [option A] or [option B]?"
- "Can you refactor [code block] to use [pattern]?"
- "Test [name] is failing. Why?"

---

## SECTION 7: DEPLOYMENT CHECKLIST

Once all 10 features are complete, use this before deploying to production:

```
PRE-DEPLOYMENT CHECKLIST:

[ ] All tests passing (pytest + frontend tests)
[ ] Environment variables set (no hardcoded secrets)
[ ] Database migrations run cleanly (staging environment)
[ ] API endpoints respond correctly (Postman or curl)
[ ] Frontend builds without errors (npm run build)
[ ] SSL certificates valid (Vercel + Railway)
[ ] Rate limiting working (simulate excess requests)
[ ] Error logging to Sentry working
[ ] GitHub API rate limiting tested
[ ] Graceful degradation tested (simulate API failures)
[ ] WebSocket streaming tested (real team analysis)
[ ] Mobile responsiveness checked
[ ] Documentation matches code (README up-to-date)
[ ] Demo video recorded (4 min walkthrough)
[ ] GitHub repo has meaningful commit history (20+ commits)
[ ] Changelog updated (what's new in v1.0)

DEPLOY STEPS:
1. Merge PR to main branch
2. GitHub Actions CI passes
3. Merge to deploy branch (triggers Railway deploy)
4. Wait for Railway build + deployment (5-10 min)
5. Check Railway logs (no errors, health check passing)
6. Run prod smoke tests (analyze real team)
7. Verify Vercel deployed (check frontend loading)
8. Smoke test frontend (login → dashboard → analyze)
9. Monitor Sentry for errors (first 30 min)

LAUNCH:
- Share on HackerNews, ProductHunt, LinkedIn
- Share demo video
- Email beta users
```

---

## FINAL NOTES

- **Claude Code is powerful**: It can read your entire codebase, understand context, and write production-ready code. Trust it.
- **Be specific**: The more details you give, the better Claude performs. Use these templates.
- **Ask, don't assume**: If a requirement is ambiguous, ask Claude to clarify before building.
- **Iterate fast**: Build → test → review → next feature. Don't get stuck perfecting one feature.
- **Save this document**: Reference it throughout development.

Good luck building GitSyntropy! 🚀
