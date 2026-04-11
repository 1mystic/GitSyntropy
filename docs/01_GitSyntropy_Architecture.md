# GITSYNTROPY: AGENTIC TEAM RESILIENCE PLATFORM
## Full Architecture & Project Plan — 2026

**Version:** 2.0 (Agentic Rebuild)  
**Conceptual Foundation:** Vedic Ashtakoot Compatibility Framework  
**Architecture Pattern:** Multi-Agent Orchestration  
**Stack:** FastAPI · LangGraph · Astro.js · Supabase · Claude API  
**Timeline:** May → August 2026

---

## PART I: THE VISION

### 1.1 The Conceptual Foundation: Vedic Ashtakoot as Signal

Ancient Indian astrology developed the Ashtakoot system — a framework for measuring compatibility between two individuals across eight dimensions (Gunas), each weighted differently, summing to a total of 36 points. This "Gun Milan" (quality matching) system has predicted relationship compatibility for centuries. It is not superstition. It is structured, weighted, multi-dimensional scoring — exactly what modern team dynamics science independently arrived at.

GitSyntropy takes this insight seriously. Not the astrology — the framework. The idea that compatibility can be decomposed into eight orthogonal dimensions, each with a different weight, and that the aggregate score predicts relationship success, is both ancient wisdom and modern organizational science. We are not building an astrology tool. We are building a team intelligence platform that honors the structural insight the Ashtakoot system discovered.

The eight Ashtakoot dimensions map to eight team dynamics dimensions, translated from behavioral signals and psychometric data:

| Vedic Guna | Points | Meaning | GitSyntropy Dimension |
|---|---|---|---|
| Nadi | 8 | Life-force compatibility | **Chronotype Sync** — peak work hour overlap |
| Bhakoot | 7 | Emotional compatibility | **Stress Response Alignment** — how members handle pressure |
| Gana | 6 | Nature type (Deva/Manushya/Rakshasa) | **Risk Tolerance** — bold vs. cautious decision-making |
| Graha Maitri | 5 | Intellectual compatibility | **Decision Framework** — data-driven vs. intuitive |
| Yoni | 4 | Instinctual compatibility | **Conflict Resolution Style** — direct vs. avoidant |
| Maitri | 3 | Social compatibility | **Communication Channel** — sync vs. async preference |
| Vashya | 2 | Influence dynamics | **Leadership Orientation** — directive vs. collaborative |
| Varna | 1 | Role alignment | **Innovation Drive** — incremental vs. disruptive |

**Total: 36 points.** Scores above 28 indicate excellent team compatibility. Below 18 indicates high friction risk.

This is not cosmetic branding. Every scoring algorithm maps directly to the Guna's behavioral interpretation, preserving both mathematical integrity and conceptual coherence. This becomes your most memorable interview story: "I rediscovered that what ancient Indian scholars figured out about compatibility, modern organizational psychology independently validated — and I built an AI agent system around it."

### 1.2 What GitSyntropy Is

GitSyntropy is an **AI-native team composition intelligence platform**. Given a set of GitHub usernames, it deploys a multi-agent pipeline that:

1. Extracts behavioral signals from GitHub commit history (chronotype, work pace, collaboration patterns)
2. Administers a short adaptive psychometric assessment (8 questions, 5 minutes)
3. Computes pairwise and team-level Ashtakoot compatibility scores
4. Generates AI-powered risk assessments, meeting time recommendations, and hiring suggestions
5. Monitors team resilience over time as team composition changes

**The agentic difference:** This is not a static algorithm that runs once. It is a persistent multi-agent system where specialized agents continuously monitor team health, surface anomalies, and proactively generate recommendations — like a team psychologist that never sleeps.

### 1.3 Why This Is Differentiated

The developer tools market is saturated with code generation (Copilot, Cursor, Devin). GitSyntropy does not compete there. It competes in the team intelligence space, which has:

- Myers-Briggs / DISC: Expensive, subjective, no data-driven component
- Lattice / 15Five: Feedback tools, not predictive analytics
- Notion / Linear: Task management, no personality-aware matching
- Hirequest / Pymetrics: One-time hiring assessments, not ongoing team monitoring

GitSyntropy's moat: **objective GitHub behavioral data** combined with **psychometric profiling** combined with **agentic monitoring** — all three together exist nowhere else.

---

## PART II: SYSTEM ARCHITECTURE

### 2.1 High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GITSYNTROPY PLATFORM                         │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    PRESENTATION LAYER                            │ │
│  │  Astro.js 4.x + React Islands + TypeScript + Tailwind CSS       │ │
│  │  Pages: Landing · Dashboard · Team Analysis · Insights · Profile │ │
│  │  Hosting: Vercel (free tier, edge CDN)                          │ │
│  └────────────────────────┬────────────────────────────────────────┘ │
│                           │ REST + WebSocket                          │
│  ┌────────────────────────▼────────────────────────────────────────┐ │
│  │                      API GATEWAY LAYER                           │ │
│  │  FastAPI 0.115+ · Async · JWT Auth · CORS · Rate Limiting        │ │
│  │  Hosting: Railway (GitHub Student Pack — no sleep)               │ │
│  └────────┬────────────────────────────────────────────┬───────────┘ │
│           │                                             │              │
│  ┌────────▼────────────────────────────────────────────▼───────────┐ │
│  │                    AGENTIC ORCHESTRATION LAYER                   │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │             ORCHESTRATOR AGENT (LangGraph)               │   │ │
│  │  │  • Parses team analysis intent from API request           │   │ │
│  │  │  • Builds agent execution DAG for the request type        │   │ │
│  │  │  • Manages inter-agent state via shared LangGraph state   │   │ │
│  │  │  • Streams intermediate results to frontend via WS        │   │ │
│  │  └───────────┬──────────────┬───────────────┬───────────────┘   │ │
│  │              │              │               │                      │ │
│  │  ┌───────────▼──┐  ┌───────▼──────┐  ┌────▼─────────────────┐  │ │
│  │  │ GITHUB       │  │ PSYCHOMETRIC │  │ COMPATIBILITY        │  │ │
│  │  │ ANALYST      │  │ AGENT        │  │ ENGINE AGENT         │  │ │
│  │  │ AGENT        │  │              │  │                      │  │ │
│  │  │ • Commit     │  │ • Adaptive   │  │ • Pairwise scores    │  │ │
│  │  │   ingestion  │  │   CAT quiz   │  │ • Team Ashtakoot     │  │ │
│  │  │ • Chronotype │  │ • 8-dim      │  │ • Variance analysis  │  │ │
│  │  │   detection  │  │   scoring    │  │ • Monte Carlo sim    │  │ │
│  │  │ • Collab     │  │ • Profile    │  │ • Risk detection     │  │ │
│  │  │   patterns   │  │   storage    │  │                      │  │ │
│  │  └───────────┬──┘  └───────┬──────┘  └────┬─────────────────┘  │ │
│  │              │              │               │                      │ │
│  │              └──────────────┴───────────────┘                     │ │
│  │                             │                                      │ │
│  │  ┌──────────────────────────▼───────────────────────────────────┐ │ │
│  │  │                  SYNTHESIS AGENT (Claude API)                 │ │ │
│  │  │  • Generates narrative team health report                     │ │ │
│  │  │  • Produces meeting time recommendations                      │ │ │
│  │  │  • Creates candidate gap-fill recommendations                 │ │ │
│  │  │  • Flags early warning signals                               │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                           │                                            │
│  ┌────────────────────────▼────────────────────────────────────────┐ │
│  │                       DATA LAYER                                  │ │
│  │  Supabase PostgreSQL + pgvector · Row Level Security             │ │
│  │  Tables: users · github_profiles · psychometric_profiles ·       │ │
│  │          teams · team_members · team_scores · score_history ·    │ │
│  │          agent_runs · agent_events · insights                    │ │
│  └────────────────────────┬────────────────────────────────────────┘ │
│                            │                                           │
│  ┌────────────────────────▼────────────────────────────────────────┐ │
│  │                    EXTERNAL INTEGRATIONS                          │ │
│  │  GitHub API v4 (GraphQL) · Claude API · Supabase Auth            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Why Astro.js (Frontend Framework Decision)

Astro.js is the right frontend framework for GitSyntropy for reasons that go beyond aesthetics:

**Architecture fit:** GitSyntropy has two fundamentally different page types — content-heavy marketing/landing pages (where Astro's static-first approach is perfect) and data-rich dashboard components (where React islands handle interactivity). Astro's island architecture lets you ship static HTML for 90% of the page and hydrate only the interactive parts.

**Performance:** Astro ships zero JavaScript by default. React components are hydrated only when visible. This gives GitSyntropy near-instant page loads — critical for first impressions on HackerNews/ProductHunt launches where users bounce within 3 seconds.

**Portfolio differentiation:** React + Vite is what everyone uses. Astro is what thoughtful engineers choose when they understand the performance tradeoffs. It signals architectural maturity to recruiters.

**SEO:** The landing page and blog posts (which you'll write for the launch) need SEO. Astro generates proper static HTML, unlike CSR React.

**React Islands for the dashboard:** The actual team analysis dashboard, real-time score visualization, and agent output streaming are all React components — `client:load` or `client:visible` directives activate them. Best of both worlds.

### 2.3 The LangGraph Agent Architecture (Deep Dive)

LangGraph is the right orchestration framework because:
- It models agent workflows as directed graphs (nodes = agents, edges = control flow)
- It handles streaming natively (results stream to frontend as each agent completes)
- It provides built-in state management across agent steps
- It supports conditional branching (if GitHub API rate-limited → skip GitHubAgent → use cached)
- It's production-grade (used by teams at Anthropic, LangChain, etc.)

**Agent State Schema:**
```python
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

class TeamAnalysisState(TypedDict):
    # Input
    team_id: str
    member_github_usernames: List[str]
    analysis_type: str  # "new_team" | "add_member" | "health_check"
    
    # GitHub Agent outputs
    github_profiles: dict          # username → GitHubProfile
    chronotype_scores: dict        # username → ChronotypeResult
    collaboration_matrix: dict     # (u1, u2) → CollaborationMetric
    github_agent_status: str       # "success" | "partial" | "cached"
    
    # Psychometric Agent outputs
    psychometric_profiles: dict    # username → PsychometricProfile
    missing_profiles: List[str]    # users who haven't completed assessment
    
    # Compatibility Engine outputs
    pairwise_scores: dict          # (u1, u2) → AshtakootScore (8 dimensions)
    team_resilience_score: float   # 0–36 composite
    weak_dimensions: List[str]     # dimensions with variance > threshold
    risk_flags: List[RiskFlag]     # specific risk signals
    
    # Synthesis Agent outputs
    narrative_report: str          # human-readable team health report
    meeting_recommendations: List[MeetingSlot]
    hiring_gap_analysis: Optional[dict]
    
    # Metadata
    run_id: str
    started_at: str
    agent_logs: List[AgentEvent]
    streaming_updates: List[StreamUpdate]
```

**LangGraph Workflow Definition:**
```python
def build_team_analysis_graph() -> StateGraph:
    workflow = StateGraph(TeamAnalysisState)
    
    # Add agent nodes
    workflow.add_node("github_analyst", github_analyst_agent)
    workflow.add_node("psychometric", psychometric_agent)
    workflow.add_node("compatibility_engine", compatibility_engine_agent)
    workflow.add_node("synthesis", synthesis_agent)
    workflow.add_node("stream_result", stream_result_handler)
    
    # Entry → parallel fetch (GitHub + Psychometric can run concurrently)
    workflow.set_entry_point("github_analyst")
    
    # After GitHub analysis → check if psychometric profiles exist
    workflow.add_conditional_edges(
        "github_analyst",
        route_after_github,
        {
            "has_all_profiles": "compatibility_engine",  # skip psychometric fetch
            "needs_profiles": "psychometric"
        }
    )
    
    # After psychometric → compatibility engine
    workflow.add_edge("psychometric", "compatibility_engine")
    
    # After compatibility → synthesis (always)
    workflow.add_edge("compatibility_engine", "synthesis")
    
    # After synthesis → stream to frontend → END
    workflow.add_edge("synthesis", "stream_result")
    workflow.add_edge("stream_result", END)
    
    return workflow.compile()
```

### 2.4 GitHub Analyst Agent (Deep Dive)

**Chronotype Detection Algorithm:**

```python
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ChronotypeResult:
    classification: str        # "night_owl" | "early_bird" | "daytime" | "flexible"
    confidence: float          # 0–1
    peak_hours: List[int]      # e.g., [21, 22, 23, 0]
    hourly_histogram: List[float]  # normalized, 24 values
    productivity_windows: List[Dict]  # [{start, end, quality_score}]

def detect_chronotype(commit_timestamps: List[datetime]) -> ChronotypeResult:
    """
    Chronotype detection using K-Means on commit timestamp distribution.
    
    Key insight: We don't just look at peak hours — we look at the SHAPE
    of the distribution. A true night owl has >40% of commits after 9pm.
    A daytime worker has a roughly normal distribution centered on business hours.
    """
    
    # Build 24-bucket hourly histogram
    hours = [ts.hour for ts in commit_timestamps]
    histogram = np.zeros(24)
    for h in hours:
        histogram[h] += 1
    histogram = histogram / histogram.sum()  # normalize to probability
    
    # Rolling window smoothing (handle midnight boundary)
    padded = np.concatenate([histogram[-3:], histogram, histogram[:3]])
    smoothed = np.convolve(padded, np.ones(7)/7, mode='valid')[:-1]
    
    # Feature extraction for classification
    night_mass = smoothed[21:].sum() + smoothed[:4].sum()    # 9pm–4am
    early_mass = smoothed[5:10].sum()                         # 5am–10am
    day_mass = smoothed[9:18].sum()                           # 9am–6pm
    peak_hour = int(np.argmax(smoothed))
    
    # Entropy-based flexibility score (high entropy = flexible schedule)
    entropy = -np.sum(smoothed * np.log(smoothed + 1e-10))
    max_entropy = np.log(24)
    flexibility = entropy / max_entropy
    
    # Classification with confidence
    if night_mass > 0.45:
        classification = "night_owl"
        confidence = min((night_mass - 0.45) * 5 + 0.6, 0.98)
    elif early_mass > 0.35 and peak_hour in range(5, 10):
        classification = "early_bird"
        confidence = min((early_mass - 0.35) * 5 + 0.6, 0.98)
    elif flexibility > 0.85:
        classification = "flexible"
        confidence = flexibility
    else:
        classification = "daytime"
        confidence = day_mass
    
    # Extract productivity windows (contiguous hours with > threshold activity)
    threshold = np.percentile(smoothed, 60)
    windows = extract_productivity_windows(smoothed, threshold)
    
    return ChronotypeResult(
        classification=classification,
        confidence=confidence,
        peak_hours=[i for i, v in enumerate(smoothed) if v > threshold],
        hourly_histogram=smoothed.tolist(),
        productivity_windows=windows
    )
```

**Collaboration Pattern Analysis:**

Beyond commit timestamps, the GitHub Analyst Agent extracts:

```python
@dataclass
class CollaborationMetrics:
    # PR dynamics
    pr_response_time_hours: float    # Avg hours to respond to PR review requests
    pr_review_thoroughness: float    # Avg comments per PR reviewed (0–1 normalized)
    review_approval_rate: float      # % of PRs approved vs. changes-requested
    
    # Communication patterns
    issue_response_time_hours: float # Avg hours to respond to issues they're mentioned in
    async_ratio: float               # ratio of async (issue/PR) vs. sync (direct commit) work
    
    # Work rhythm
    sprint_burst_score: float        # High if commits cluster in bursts with long gaps
    steady_state_score: float        # High if commits distribute evenly across days
    weekend_work_ratio: float        # % of commits on weekends (burnout signal)
    
    # Collaboration graph
    frequent_collaborators: List[str]  # usernames they often co-commit with
    collaboration_density: float       # degree in the team collaboration graph

def analyze_collaboration(
    github_events: List[GitHubEvent],
    pull_requests: List[PullRequest],
    issues: List[Issue]
) -> CollaborationMetrics:
    # Full implementation — extracts all metrics from GitHub Events API response
    pass
```

### 2.5 The Ashtakoot Compatibility Engine (Deep Dive)

The core algorithm. Computes team resilience using variance-based scoring across all 8 Ashtakoot dimensions.

```python
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

# Dimension weights mirror the original Ashtakoot point system
ASHTAKOOT_WEIGHTS = {
    "chronotype_sync":      8,   # Nadi — highest weight, life-force compatibility
    "stress_response":      7,   # Bhakoot — emotional compatibility
    "risk_tolerance":       6,   # Gana — nature type
    "decision_framework":   5,   # Graha Maitri — intellectual compatibility
    "conflict_resolution":  4,   # Yoni — instinctual compatibility
    "communication_channel":3,   # Maitri — social compatibility
    "leadership_orientation":2,  # Vashya — influence dynamics
    "innovation_drive":     1    # Varna — role alignment
}
# Total: 36 points

@dataclass
class AshtakootScore:
    total: float                        # 0–36
    pct: float                          # 0–100
    level: str                          # "Excellent" | "Good" | "Fair" | "Poor"
    dimension_scores: Dict[str, float]  # per-dimension sub-scores
    weak_dimensions: List[str]          # dimensions scoring < 30% of max
    strong_dimensions: List[str]        # dimensions scoring > 80% of max
    risk_flags: List[str]               # specific human-readable risk signals
    confidence: float                   # based on data completeness

def compute_team_ashtakoot(
    member_profiles: List[MemberProfile]
) -> AshtakootScore:
    """
    Compute the team's Ashtakoot score.
    
    Scoring philosophy: alignment matters more than absolute values.
    A team of all risk-takers scores poorly. A team of one risk-taker
    and seven conservatives also scores poorly. The ideal is slight 
    complementarity within a tolerance band — not uniformity, not chaos.
    
    We use a modified variance penalty:
    score(dim) = W(dim) × f(variance, n_members)
    where f penalizes both extreme uniformity and extreme diversity.
    
    For small teams (n ≤ 4): use exponential variance decay
    For larger teams (n > 4): use a bimodal tolerance band (allows sub-teams)
    """
    n = len(member_profiles)
    dimension_scores = {}
    risk_flags = []
    
    for dim, weight in ASHTAKOOT_WEIGHTS.items():
        values = [p.get_dimension(dim) for p in member_profiles]
        values = np.array(values)
        
        mean = np.mean(values)
        variance = np.var(values)
        
        if n <= 4:
            # Small team: low variance = alignment = good
            # Perfect alignment (var=0): score = weight (max)
            # High variance (var=1): score → 0
            penalty_factor = np.exp(-2 * variance)
            
        else:
            # Larger team: some variance is healthy (diverse perspectives)
            # Penalize both too-low (groupthink) and too-high (chaos)
            # Optimal variance band: 0.05–0.20
            optimal_center = 0.12
            penalty_factor = np.exp(-((variance - optimal_center) ** 2) / (2 * 0.08 ** 2))
        
        # Additional penalty: chronotype_sync (Nadi) is critical
        # If any two members are > 6 hours apart in peak hours, hard penalty
        if dim == "chronotype_sync":
            max_hour_gap = compute_max_hour_gap(member_profiles)
            if max_hour_gap > 6:
                penalty_factor *= 0.5  # 50% penalty for severe chronotype mismatch
                risk_flags.append(
                    f"Severe chronotype mismatch: {max_hour_gap:.0f}h gap between "
                    f"peak productivity windows — async-first workflows required"
                )
        
        dim_score = weight * penalty_factor
        dimension_scores[dim] = round(dim_score, 2)
        
        # Flag weak dimensions
        if dim_score < weight * 0.3:
            risk_flags.append(
                f"Critical misalignment in {dim.replace('_', ' ')} "
                f"({dim_score:.1f}/{weight} pts) — active management required"
            )
    
    total = sum(dimension_scores.values())
    pct = (total / 36) * 100
    
    if total >= 28:
        level = "Excellent"
    elif total >= 20:
        level = "Good"
    elif total >= 12:
        level = "Fair"
    else:
        level = "Poor"
    
    weak = [d for d, s in dimension_scores.items() if s < ASHTAKOOT_WEIGHTS[d] * 0.30]
    strong = [d for d, s in dimension_scores.items() if s > ASHTAKOOT_WEIGHTS[d] * 0.80]
    
    # Confidence: based on what percentage of profiles are complete
    complete_profiles = sum(1 for p in member_profiles if p.is_complete)
    confidence = complete_profiles / n
    
    return AshtakootScore(
        total=round(total, 1),
        pct=round(pct, 1),
        level=level,
        dimension_scores=dimension_scores,
        weak_dimensions=weak,
        strong_dimensions=strong,
        risk_flags=risk_flags,
        confidence=confidence
    )
```

**Monte Carlo Candidate Simulation:**

When used for hiring recommendations, the engine simulates what happens to the team score if a candidate is added:

```python
def simulate_candidate_impact(
    current_team: List[MemberProfile],
    candidate: MemberProfile,
    n_simulations: int = 1000
) -> CandidateImpactReport:
    """
    Monte Carlo simulation of team resilience with candidate added.
    
    Why Monte Carlo? Profiles have uncertainty (assessment scores aren't perfect).
    We sample from a distribution around each score to get a realistic range.
    """
    baseline_score = compute_team_ashtakoot(current_team).total
    impact_scores = []
    
    for _ in range(n_simulations):
        # Perturb each profile slightly (Gaussian noise, σ=0.05)
        perturbed_team = [p.sample_with_noise(sigma=0.05) for p in current_team]
        perturbed_candidate = candidate.sample_with_noise(sigma=0.05)
        
        simulated_score = compute_team_ashtakoot(
            perturbed_team + [perturbed_candidate]
        ).total
        impact_scores.append(simulated_score)
    
    impact_array = np.array(impact_scores)
    
    return CandidateImpactReport(
        baseline_score=baseline_score,
        predicted_score_mean=np.mean(impact_array),
        predicted_score_p10=np.percentile(impact_array, 10),
        predicted_score_p90=np.percentile(impact_array, 90),
        improvement_probability=np.mean(impact_array > baseline_score),
        fills_dimensions=[d for d in identify_gaps(current_team)
                          if candidate.closes_gap(d, current_team)]
    )
```

### 2.6 Synthesis Agent (Claude API Integration)

The Synthesis Agent takes all structured outputs from the other agents and generates human-readable intelligence. This is where Claude API is used.

```python
async def synthesis_agent(state: TeamAnalysisState) -> TeamAnalysisState:
    """
    Synthesis Agent: Convert structured scores into actionable intelligence.
    Uses Claude API with structured context injection.
    """
    
    system_prompt = """
You are a team dynamics specialist with deep expertise in organizational psychology 
and software engineering team structures. You analyze team compatibility data and 
produce concise, actionable reports.

Your framework draws on:
- Vedic Ashtakoot compatibility theory (8 dimensions, 36-point system)
- Patrick Lencioni's Five Dysfunctions of a Team
- Tuckman's stages of team development
- Modern research on remote engineering team effectiveness

IMPORTANT CONSTRAINTS:
- Be specific, not generic. Reference the actual dimension scores.
- Do not recommend what you cannot justify from the data.
- Flag uncertainty clearly when data is incomplete.
- Keep the narrative to 3–4 paragraphs maximum.
- Recommendations must be immediately actionable (not platitudes).
"""
    
    context = f"""
TEAM ANALYSIS INPUT:

Team Composition: {state['member_github_usernames']}
Members Analyzed: {len(state['member_github_usernames'])}

ASHTAKOOT SCORES:
{format_dimension_scores(state['pairwise_scores'], state['team_resilience_score'])}

CHRONOTYPE DATA:
{format_chronotype_data(state['github_profiles'])}

RISK FLAGS:
{chr(10).join(f'• {flag}' for flag in state['risk_flags'])}

WEAK DIMENSIONS: {state['weak_dimensions']}
STRONG DIMENSIONS: {state.get('strong_dimensions', [])}

Analyze this team's compatibility and produce:
1. TEAM HEALTH NARRATIVE (3 paragraphs): Current state, key risks, key strengths
2. MEETING WINDOWS: Top 3 optimal meeting time slots based on chronotype overlap
3. IMMEDIATE ACTIONS: 3 specific, actionable recommendations
4. HIRING GAP (if applicable): What type of person would most improve this team
"""
    
    response = await anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=system_prompt,
        messages=[{"role": "user", "content": context}],
        stream=True
    )
    
    # Stream the response to frontend via WebSocket
    full_response = ""
    async for chunk in response:
        if chunk.type == "content_block_delta":
            delta = chunk.delta.text
            full_response += delta
            await state['websocket'].send_json({
                "event": "synthesis_streaming",
                "delta": delta
            })
    
    state['narrative_report'] = full_response
    return state
```

### 2.7 Database Schema (Complete)

```sql
-- ==========================================
-- GITSYNTROPY DATABASE SCHEMA v2.0
-- PostgreSQL via Supabase free tier
-- ==========================================

-- Users (GitHub OAuth authenticated)
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id   BIGINT UNIQUE NOT NULL,
    username    VARCHAR(100) UNIQUE NOT NULL,
    email       VARCHAR(255),
    name        VARCHAR(255),
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- GitHub behavioral profiles (extracted by GitHubAnalystAgent)
CREATE TABLE github_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Chronotype detection
    chronotype          VARCHAR(20),          -- night_owl | early_bird | daytime | flexible
    chronotype_confidence FLOAT,              -- 0–1
    peak_hours          INT[],                -- Array of peak productivity hours
    hourly_histogram    FLOAT[],              -- 24-bucket normalized histogram
    
    -- Work rhythm
    sprint_burst_score  FLOAT,
    steady_state_score  FLOAT,
    weekend_work_ratio  FLOAT,
    
    -- Collaboration
    pr_response_time_hours  FLOAT,
    review_thoroughness     FLOAT,
    async_ratio             FLOAT,
    
    -- Raw data
    total_commits           INT,
    analyzed_days           INT,              -- how many days of history analyzed
    last_commit_at          TIMESTAMPTZ,
    
    -- Metadata
    last_synced_at  TIMESTAMPTZ,
    sync_status     VARCHAR(20) DEFAULT 'pending',  -- pending | syncing | synced | failed
    raw_data        JSONB,                    -- full GitHub API response (compressed)
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Psychometric profiles (8 Ashtakoot dimensions)
CREATE TABLE psychometric_profiles (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 8 Ashtakoot Dimensions (0.0 – 1.0 scale)
    chronotype_sync         FLOAT NOT NULL,   -- Nadi     (8 pts) - derived from GitHub
    stress_response         FLOAT NOT NULL,   -- Bhakoot  (7 pts) - from assessment
    risk_tolerance          FLOAT NOT NULL,   -- Gana     (6 pts) - from assessment
    decision_framework      FLOAT NOT NULL,   -- Graha    (5 pts) - from assessment
    conflict_resolution     FLOAT NOT NULL,   -- Yoni     (4 pts) - from assessment
    communication_channel   FLOAT NOT NULL,   -- Maitri   (3 pts) - from assessment
    leadership_orientation  FLOAT NOT NULL,   -- Vashya   (2 pts) - from assessment
    innovation_drive        FLOAT NOT NULL,   -- Varna    (1 pt)  - from assessment + GitHub
    
    -- Assessment metadata
    assessment_version      VARCHAR(10) DEFAULT '2.0',
    completed_at            TIMESTAMPTZ,
    response_time_seconds   INT,              -- how long they took (data quality signal)
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Teams
CREATE TABLE teams (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    created_by  UUID REFERENCES users(id),
    invite_token VARCHAR(64) UNIQUE,          -- for invite link flow
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Team membership
CREATE TABLE team_members (
    team_id     UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        VARCHAR(100),
    joined_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (team_id, user_id)
);

-- Team Ashtakoot scores (versioned — stored on every recalculation)
CREATE TABLE team_scores (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id                 UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    
    -- Composite score
    resilience_score        FLOAT NOT NULL,   -- 0–36
    compatibility_pct       FLOAT NOT NULL,   -- 0–100
    level                   VARCHAR(20),      -- Excellent | Good | Fair | Poor
    confidence              FLOAT,            -- 0–1 (based on data completeness)
    
    -- Dimension breakdown
    dimension_scores        JSONB NOT NULL,   -- {dim: score} for all 8 dimensions
    weak_dimensions         TEXT[],
    strong_dimensions       TEXT[],
    risk_flags              TEXT[],
    
    -- Agent outputs
    narrative_report        TEXT,             -- Claude-generated narrative
    meeting_recommendations JSONB,            -- [{start, end, quality_score}]
    hiring_gap_analysis     JSONB,            -- if team has open slots
    
    -- Pairwise data
    pairwise_scores         JSONB,            -- {(u1,u2): AshtakootScore}
    
    -- Metadata
    agent_run_id            UUID,
    member_snapshot         UUID[],           -- which users were in team at calculation time
    calculated_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Agent execution audit log
CREATE TABLE agent_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id         UUID REFERENCES teams(id),
    run_type        VARCHAR(50),              -- new_team | add_member | health_check
    status          VARCHAR(20),             -- running | completed | failed
    agent_events    JSONB,                   -- array of {agent, status, duration_ms}
    error           TEXT,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_github_profiles_user ON github_profiles(user_id);
CREATE INDEX idx_psychometric_user ON psychometric_profiles(user_id);
CREATE INDEX idx_team_members_team ON team_members(team_id);
CREATE INDEX idx_team_members_user ON team_members(user_id);
CREATE INDEX idx_team_scores_team ON team_scores(team_id);
CREATE INDEX idx_team_scores_calculated ON team_scores(calculated_at DESC);
CREATE INDEX idx_teams_invite_token ON teams(invite_token);

-- Row Level Security (Supabase)
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_scores ENABLE ROW LEVEL SECURITY;

-- Users can only see teams they belong to
CREATE POLICY "team_member_access" ON teams
    FOR SELECT USING (
        id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())
        OR created_by = auth.uid()
    );
```

---

## PART III: TECH STACK SPECIFICATION

### 3.1 Backend (Python)

```
Runtime:        Python 3.12
Framework:      FastAPI 0.115+ (async, OpenAPI auto-docs)
Agent Layer:    LangGraph 0.2+ (agent orchestration, state management)
LLM Client:     anthropic SDK 0.40+ (streaming, tool use)
GitHub Client:  PyGithub 2.x + gql (GraphQL for efficiency)
DB Client:      sqlalchemy 2.0 async + asyncpg (Supabase PostgreSQL)
Auth:           python-jose (JWT) + httpx (GitHub OAuth flow)
Validation:     Pydantic v2 (data models, strict typing)
Logging:        structlog (structured, searchable logs)
Testing:        pytest + pytest-asyncio + httpx (async test client)
Linting:        ruff (fast, replaces flake8/isort/black)
```

### 3.2 Frontend (Astro + React Islands)

```
Framework:      Astro 4.x
React Islands:  React 18 + @astrojs/react
Styling:        Tailwind CSS 3.x
Charts:         recharts (score visualizations) + d3 (chronotype heatmaps)
State:          nanostores (Astro-native, tiny) for cross-island state
HTTP Client:    @tanstack/query (data fetching, caching, invalidation)
WebSocket:      native WebSocket API (streaming agent outputs)
Animation:      Framer Motion (React islands) + CSS animations (Astro)
Build:          Vite 5.x (Astro's default)
Deployment:     Vercel (astro/vercel adapter, edge runtime)
```

### 3.3 Infrastructure (All Free)

```
Frontend:       Vercel (hobby tier — no sleep, global CDN, auto-HTTPS)
Backend:        Railway (GitHub Student Pack — $5–10/mo credit)
Database:       Supabase (free tier: 500MB, 2GB transfer, 50K auth users)
CI/CD:          GitHub Actions (2000 min/mo free with GitHub Pro/Student Pack)
Monitoring:     Sentry free tier (5M events/mo, GitHub Student Pack access)
Domain:         gitsyntropy.dev via Namecheap (1yr free, GitHub Student Pack)
Secrets:        Railway secret variables + Vercel environment variables
LLM:            Claude API (haiku-4-5-20251001 — ~$0.25/1M tokens input)
```

---

## PART IV: API SPECIFICATION

### 4.1 Core Routes

```
Authentication:
  GET  /api/v1/auth/github              → Redirect to GitHub OAuth
  GET  /api/v1/auth/callback            → Handle OAuth, return JWT
  POST /api/v1/auth/refresh             → Refresh JWT

Users:
  GET  /api/v1/me                       → Current user profile + profiles
  POST /api/v1/me/psychometric          → Submit psychometric assessment
  POST /api/v1/me/github/sync           → Trigger GitHub data sync (background)
  GET  /api/v1/me/github/sync/status    → Poll sync status

Teams:
  POST /api/v1/teams                    → Create team
  GET  /api/v1/teams/{id}               → Get team + members + latest score
  POST /api/v1/teams/{id}/members       → Add member (by github username)
  DELETE /api/v1/teams/{id}/members/{uid} → Remove member
  GET  /api/v1/teams/{id}/invite        → Get/generate invite link
  GET  /api/v1/teams/join/{token}       → Join via invite token

Analysis:
  POST /api/v1/teams/{id}/analyze       → Trigger full Ashtakoot analysis (async)
  GET  /api/v1/teams/{id}/analysis/status/{run_id} → Poll analysis status
  GET  /api/v1/teams/{id}/scores        → Score history (pagination)
  GET  /api/v1/teams/{id}/scores/latest → Latest score with full report

WebSocket:
  WS   /ws/teams/{id}/analysis/{run_id} → Stream agent events to frontend

Insights:
  GET  /api/v1/teams/{id}/candidates    → Candidate ranking for open roles
  POST /api/v1/simulate                 → Simulate candidate impact (no save)
```

### 4.2 WebSocket Event Schema

```json
// Events streamed during analysis
{"event": "agent_started",     "agent": "github_analyst", "timestamp": "..."}
{"event": "agent_progress",    "agent": "github_analyst", "message": "Analyzing 847 commits...", "pct": 45}
{"event": "agent_completed",   "agent": "github_analyst", "result": {...}, "duration_ms": 2340}
{"event": "agent_started",     "agent": "compatibility_engine", "timestamp": "..."}
{"event": "score_computed",    "resilience_score": 24.3, "dimension_scores": {...}}
{"event": "synthesis_streaming","delta": "The team shows strong chronotype..."}
{"event": "synthesis_complete", "report": "...", "recommendations": [...]}
{"event": "analysis_done",     "run_id": "...", "total_duration_ms": 8420}
```

---

## PART V: FRONTEND DESIGN (ASTRO)

### 5.1 Page Architecture

```
src/
├── pages/
│   ├── index.astro           # Landing page (static, SEO-optimized)
│   ├── auth/
│   │   └── callback.astro    # OAuth callback handler
│   ├── dashboard/
│   │   └── index.astro       # Teams overview (React island for data)
│   ├── team/
│   │   └── [id].astro        # Team analysis page (multiple React islands)
│   └── profile/
│       └── index.astro       # User profile + assessment
├── components/
│   ├── astro/                # Pure Astro components (no JS shipped)
│   │   ├── Navbar.astro
│   │   ├── Hero.astro
│   │   └── FeatureSection.astro
│   └── react/                # React islands (hydrated on client)
│       ├── TeamDashboard.tsx  # client:load
│       ├── AshtakootRadar.tsx # Radar chart of 8 dimensions — client:visible
│       ├── ChronotypeHeatmap.tsx # D3 24h heatmap — client:visible
│       ├── AgentStream.tsx    # WebSocket streaming UI — client:load
│       ├── Psychometric.tsx   # Assessment form — client:load
│       └── CandidateSim.tsx   # Candidate impact simulator — client:load
├── layouts/
│   ├── Base.astro
│   └── App.astro             # Authenticated layout
└── lib/
    ├── api.ts                 # API client (fetch wrappers)
    ├── auth.ts                # JWT handling
    └── store.ts               # nanostores for cross-island state
```

### 5.2 Key UI Patterns

**Ashtakoot Radar Chart (React + recharts):**
A radar/spider chart showing all 8 dimensions for each team member overlaid — visual representation of where alignment exists and where gaps appear. Each dimension maps to one of the 8 Vedic Gunas with tooltip explanations.

**Chronotype Heatmap (React + D3):**
A 24-hour × team-member heatmap showing when each person is most productive (derived from commit timestamps). Overlapping high-activity hours are highlighted in green — these are the ideal meeting windows.

**Agent Stream View (React + WebSocket):**
As analysis runs, a live terminal-style feed shows which agent is running, what it found, and streams the synthesis report character by character. This is the "wow" moment of the product.

**Score History Timeline (React + recharts):**
Line chart showing the team's Ashtakoot score over time as members join/leave. A dashed vertical line marks when a member was added or removed, annotated with their impact.

---

## PART VI: WEEKLY ROADMAP (16 WEEKS)

### May: Foundation + Core Agents

**Week 1 (May 4–10): Project Setup**
- Initialize Astro 4.x project with React integration + Tailwind
- FastAPI skeleton with JWT auth + GitHub OAuth flow
- Supabase project: run schema migrations
- Railway deployment: FastAPI container live
- Vercel deployment: Astro frontend live
- GitHub Actions: lint + test CI pipeline

**Week 2 (May 11–17): GitHub Analyst Agent**
- GitHub GraphQL client (PyGithub + gql)
- Commit timestamp extraction (90-day history)
- Chronotype detection algorithm (K-Means implementation)
- Collaboration metrics extraction (PR response time, review patterns)
- Background task: GitHub sync via FastAPI BackgroundTasks
- Sync status polling endpoint

**Week 3 (May 18–24): Psychometric Agent**
- 8-question assessment API (submit + retrieve)
- Score computation for all 8 Ashtakoot dimensions
- Adaptive question ordering (CAT: harder questions if initial answers suggest extreme scores)
- Profile storage in Supabase
- Frontend: Assessment form component (Astro page + React island)

**Week 4 (May 25–31): Compatibility Engine Agent**
- Variance-weighted Ashtakoot scoring (all 8 dimensions)
- Pairwise score matrix for team members
- Risk flag detection (critical misalignment conditions)
- Monte Carlo candidate simulation (1000 iterations)
- Unit tests for all scoring functions (pytest, 100% coverage on algorithms)

### June: Orchestration + Synthesis + Frontend

**Week 5 (June 1–7): LangGraph Orchestration**
- LangGraph state schema definition
- Agent DAG construction (all 4 agents + conditional routing)
- WebSocket endpoint for streaming agent events
- Agent audit log (agent_runs table)
- End-to-end test: analyze a real team (use your IITM project team)

**Week 6 (June 8–14): Claude Synthesis Integration**
- Synthesis agent: Claude API with structured context injection
- Streaming response → WebSocket → frontend
- Meeting window recommendations (chronotype-based)
- Hiring gap analysis (which dimension is weakest, what profile fills it)
- Prompt tuning: iterate until recommendations are specific and actionable

**Week 7 (June 15–21): Frontend Dashboard**
- Team overview page (list teams, latest scores, status indicators)
- Ashtakoot radar chart (recharts, all 8 dimensions per member)
- Chronotype heatmap (D3, 24h overlap visualization)
- Agent stream view (WebSocket, live analysis terminal)
- Score history timeline (recharts line chart with member change annotations)

**Week 8 (June 22–28): Team Management UX**
- Team creation flow
- Invite link system (generate → share → accept → auto-join)
- Member removal with score impact preview
- Candidate simulator UI (add hypothetical member → see simulated score change)
- Demo mode: pre-populated fake team data for visitors who haven't authenticated

### July: Polish + Launch + Documentation

**Week 9 (July 1–7): Error Handling + Performance**
- GitHub API rate limit handling (exponential backoff, cached fallback)
- Loading states for all async operations (skeleton screens, not spinners)
- Graceful degradation: if psychometric not complete → partial score with disclaimer
- P95 latency target: full analysis < 10s (profile it, optimize hot paths)
- Sentry integration (error tracking, GitHub Student Pack)

**Week 10 (July 8–14): README + Demo Video**
- Complete README: problem → solution → architecture → quick start → screenshots
- Architecture diagram (draw.io or Excalidraw, PNG in repo)
- 4-minute demo video (Loom): GitHub sync → psychometric → team analysis → streaming agent output → radar chart → hiring gap
- GitHub repo: 20+ meaningful commits, proper branch strategy, closed issues

**Week 11 (July 15–21): Launch**
- HackerNews: "Show HN: I used Vedic Ashtakoot compatibility theory to model team dynamics with AI agents"
- ProductHunt: prepare assets (logo, screenshots, 60-second GIF)
- dev.to article: "How Ancient Indian Astrology Inspired My Team Analytics Algorithm"
- LinkedIn post: the algorithmic story (Gun Milan → Ashtakoot → team dynamics)

**Week 12 (July 22–28): Interview Preparation**
- Whiteboard architecture walkthrough (practice 5-minute version)
- Algorithm explanation (variance-weighted scoring, chronotype detection)
- "How would you scale to 10K teams?" answer
- "What did you learn building this?" answer
- Prepare code walkthrough (LangGraph orchestration + Ashtakoot scoring)

### August: Applications + Optimization

**Weeks 13–16:** Apply to target companies with GitSyntropy as primary project. Collect user feedback, fix critical bugs, optimize based on production data. Write case study for portfolio.

---

## PART VII: POSITIONING

### 7.1 What You Claim in Interviews

- "I built a multi-agent AI system using LangGraph that orchestrates four specialized agents — GitHub Analyst, Psychometric, Compatibility Engine, and Synthesis — to analyze team dynamics and produce actionable hiring recommendations"
- "The core algorithm is a variance-weighted 8-dimension scoring system inspired by the Vedic Ashtakoot compatibility framework — same mathematical structure, modern behavioral science interpretation"
- "I chose Astro.js for the frontend because it ships zero JavaScript by default — React islands are only hydrated for interactive components, giving sub-second page loads critical for user retention on launch day"
- "The system uses Monte Carlo simulation to predict how a candidate hire will change the team's resilience score — 1000 iterations with Gaussian perturbation of profile scores"

### 7.2 The Story No One Else Has

"I was reading about ancient Indian Kundali matching when I realized the Ashtakoot system — eight compatibility dimensions, each differently weighted, summing to 36 — is mathematically identical to what modern organizational psychologists designed for team effectiveness. The Vedic scholars figured out that compatibility is multi-dimensional and weighted 1500 years ago. I built an AI agent system that implements this insight with GitHub behavioral data as the objective signal."

That story is memorable. No competing candidate has it.
