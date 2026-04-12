# GitSyntropy — Research Paper Plan
## "Predicting Software Team Compatibility via Behavioral Telemetry and Adaptive Psychometric Profiling"

**Document version:** 1.0 — 2026-04-12  
**Purpose:** Complete, hallucination-proof context for any LLM (or human) to write each paper section correctly, citing real sources, with the exact algorithms and formulas implemented in this codebase.  
**Audience:** Any researcher or AI assistant contributing to this paper. Read every section before writing anything.

---

## Part 0 — Strategy: Paper vs. Patent

### Why a Conference Paper First

Filing a process patent in India (Indian Patent Act, Section 3(k) excludes pure mathematical methods but allows technical process patents involving a computer system) is viable but slow: 18–36 months to grant, requires a patent agent, and prior publication can bar filing in some jurisdictions unless you file a provisional first. The **recommended sequence** is:

1. File a **Provisional Patent Application (PPA)** with the Indian Patent Office (IPO) — this costs ~₹1,600 (individual) and gives 12 months of "patent pending" status, locking your priority date.
2. Within those 12 months, submit to a conference.
3. After acceptance and publication, convert PPA to a complete specification.

**The provisional claim** protects: (a) the circular-coordinate K-Means chronotype method applied to VCS commit timestamps, (b) the weighted 8-dimensional compatibility engine combining behavioral telemetry with adaptive psychometric data, and (c) the Monte Carlo candidate simulation method for hire-impact prediction.

### Target Venue (Primary)

**MSR — IEEE/ACM International Conference on Mining Software Repositories**  
- MSR is the premier venue for empirical studies of GitHub/version-control data.  
- Acceptance rate: ~25%. Full papers are 10 pages + references.  
- Typical submission window: January, notification March, camera-ready April, conference May.
- Your paper fits MSR because it mines GitHub behavioral traces for team analytics.

**Backup venues:**  
- **CSCW** (ACM Computer-Supported Cooperative Work) — if emphasis shifts to the team collaboration framing.  
- **PAKDD** (Pacific-Asia Knowledge Discovery and Data Mining) — strong India/Asia participation, good for the ML-heavy framing.  
- **COMAD/IKDD** (India-specific) — if you want a domestic publication first.  
- **EMSE journal** (Empirical Software Engineering, Springer) — for the long-form with full evaluation data.

### Paper Length and Format

- MSR: 10-page double-column IEEE format + unlimited references.  
- Use IEEEtran LaTeX template.  
- Figures count toward the page limit; plan for ~5 key figures.

---

## Part 1 — Ground Truth: Exact System Specification

**CRITICAL: Every claim in the paper must be grounded in one of the following facts. Do not invent numbers, claims, or behaviors that are not here.**

### 1.1 Chronotype Detection Algorithm (file: `apps/backend/app/github_client.py`)

**Input:** A list of integer commit hours (0–23) extracted from GitHub commit author timestamps over the past 90 days.

**Step 1 — Circular coordinate mapping:**  
Each hour `h` is mapped to a 2D unit-circle point:
```
x = cos(2π × h / 24)
y = sin(2π × h / 24)
```
This handles the discontinuity at midnight: hour 23 and hour 0 are adjacent in circular space even though they are 23 apart in linear space.

**Step 2 — K-Means in circular space:**  
`k = min(3, |unique_hours|)`, `random_state=42`, `n_init=10`.  
Applied via scikit-learn `KMeans` on the (x, y) coordinate matrix.

**Step 3 — Dominant cluster extraction:**  
The cluster with the most commits is the dominant cluster. Confidence = `dominant_cluster_count / total_commits`.  
The cluster centroid (cx, cy) is converted back to a peak hour:
```
angle = atan2(cy, cx)
if angle < 0: angle += 2π
peak_hour = angle × 24 / (2π)
```

**Step 4 — Entropy-based "flexible" detection:**  
Shannon entropy of the 24-bin normalized histogram:
```
H = -Σ p_i × log(p_i + 1e-9)    for i in 0..23
H_max = log(24)
if H / H_max > 0.92: label = "flexible"
```

**Step 5 — Label assignment:**  
```
peak_hour in [5, 11)  → "lark"    (early bird)
peak_hour in [11, 19) → "daytime"
peak_hour in [19, 23) → "evening"
else                  → "owl"     (night owl, covers 23–5)
```

**Fallback for < 10 commits:** Peak of histogram used directly (no clustering). Confidence fixed at 0.4.

**Fallback for empty input:** Returns `{"chronotype": "flexible", "peak_hour": 12.0, "confidence": 0.0}`.

---

### 1.2 Compatibility Scoring Engine (file: `apps/backend/app/services.py`, function `compatibility`)

**Framework basis:** The Ashtakoot ("eight-koot") system from Vedic jyotish, originally used to score marriage compatibility across 8 attributes with a total of 36 "gunas" (points). We repurpose its weight structure for software team behavioral compatibility.

**The 8 dimensions and their weights (total max = 36 points):**

| # | Internal Key | English Label | Weight (max pts) | Measures |
|---|---|---|---|---|
| 1 | `varna_alignment` | Innovation Drive | 1 | Conservative vs. exploratory orientation |
| 2 | `vashya_influence` | Leadership Orientation | 2 | Authority and influence patterns |
| 3 | `tara_resilience` | Team Resilience | 3 | Communication style fit |
| 4 | `yoni_workstyle` | Work Style | 4 | Conflict resolution / work mode |
| 5 | `graha_maitri_cognition` | Decision Style | 5 | Data-driven vs. intuitive |
| 6 | `gana_temperament` | Risk Tolerance | 6 | Bold vs. cautious |
| 7 | `bhakoot_strategy` | Stress Response | 7 | Pressure handling patterns |
| 8 | `nadi_chronotype_sync` | Chronotype Sync | 8 | Peak-hour overlap (from GitHub) |

**Scoring formula for each dimension d:**
```
similarity_d = max(0, 1 - |score_a_d - score_b_d| / weight_d)
dim_score_d  = round(similarity_d × weight_d, 2)
```

**Missing data imputation:** If `score_a_d` or `score_b_d` is `None`, substitute `weight_d × 0.5` (neutral midpoint). The `data_gaps` set records which dimensions had missing data.

**Aggregation:**
```
total_score = Σ dim_score_d    (d over all 8 dimensions)
score_pct   = (total_score / 36) × 100
```

**Level classification:**
```
total ≥ 28 → "excellent"
total ≥ 20 → "good"
total ≥ 12 → "fair"
total < 12 → "poor"
```

**Weak/Strong classification per dimension:**
```
dim_score < weight × 0.3 → "weak"   (also added to risk_flags)
dim_score > weight × 0.8 → "strong"
otherwise                → "balanced"
```

**Confidence metric:**
```
confidence = observed_signal_count / (len(dimensions) × 2)
```
Where `observed_signal_count` = number of non-None scores across both members (max 16).

**Special chronotype risk flag:** If `nadi_chronotype_sync < 8 × 0.45 = 3.6`, the flag "Chronotype sync is weak; consider async-first collaboration rituals." is emitted.

---

### 1.3 Computerized Adaptive Testing (CAT) (file: `apps/backend/app/services.py`, function `cat_select_next_question`)

**Standard CAT** selects the next item to maximize information gain given current ability estimates (Rasch/IRT models). GitSyntropy uses a **greedy weight-maximization approximation** suited to a small (8-item) fixed bank:

**Algorithm:**
1. Start with the highest-weight unanswered question (always q8 = Chronotype Sync = 8 pts).
2. Pick the next highest-weight unanswered question at each step.
3. **Early-stop criterion:** Once `len(answered) ≥ 4` AND `answered_weight / 36 ≥ 0.70` AND no unanswered question has weight ≥ 4, declare the profile "confident enough".

**Question bank (8 items, ordered by dimension weight):**

| ID | Prompt | Left Label | Right Label | Dimension | Weight |
|---|---|---|---|---|---|
| q1 | Decision style in uncertainty | Intuitive | Analytical | Innovation Drive | 1 |
| q2 | Preferred delivery rhythm | Steady | Bursty | Leadership Orientation | 2 |
| q3 | Conflict handling pattern | Direct | Diplomatic | Team Resilience | 3 |
| q4 | Team interaction mode | Independent | Collaborative | Work Style | 4 |
| q5 | Context switching tolerance | Low | High | Decision Style | 5 |
| q6 | Communication density | Concise | Detailed | Risk Tolerance | 6 |
| q7 | Experimentation appetite | Conservative | Exploratory | Stress Response | 7 |
| q8 | Working-hour preference | Early | Late | Chronotype Sync | 8 |

**Answer format:** Likert 1–5 scale. `score_d = (answer_value / 5) × weight_d`.

**Early stop example:** Answering q8+q7+q6+q5+q4 covers 8+7+6+5+4=30/36=83% of total weight, and all items ≥4pt are answered — system stops, saving 3 questions.

---

### 1.4 Monte Carlo Candidate Simulation (file: `apps/backend/app/services.py`, function `monte_carlo_candidate_simulation`)

**Purpose:** Given the current team's psychometric profiles, find the optimal incoming candidate profile that maximizes mean pairwise compatibility.

**Algorithm (deterministic seed = 42):**

1. Compute current team-internal mean pairwise compatibility score `μ_team` (all member pairs averaged).
2. Identify `weak_dims` = dimensions where `team_mean_d < weight_d × 0.45`.
3. For each of `n_iterations` (default 1000):
   a. Sample a candidate profile vector. For weak dimensions, sample score from `Uniform(0.5 × weight_d, 1.0 × weight_d)` (biased high). For others: `Uniform(0.15 × weight_d, 0.95 × weight_d)`.
   b. Compute mean pairwise compatibility of candidate with each team member.
   c. Compute `improvement = mean_candidate_compat - μ_team`.
   d. Track best improvement and store optimal profile.
4. Report: `mean_improvement`, `best_improvement`, `p25_improvement`, `p75_improvement` (empirical percentiles), `weak_dimensions_targeted`.

**Key property:** The simulation is **deterministic** (seed=42). Same team inputs always produce the same optimal candidate profile.

**Confidence:** Fixed at 1.0 when `n_iterations ≥ 1000`.

---

### 1.5 Orchestration Pipeline (LangGraph DAG)

**Node sequence:**
```
github_analyst_node → psychometric_profiler_node → [candidate_simulation_node →] compatibility_engine_node → synthesis_node
```

The `candidate_simulation` node is optional (triggered by `include_candidates=True`).

Each node is an async Python function receiving and returning a typed `OrchestratorState` TypedDict. LangGraph handles edge routing. The pipeline runs on WebSocket connection; each node emits a progress event streamed to the client.

**Synthesis node** calls the Anthropic Claude API (`claude-sonnet-4-6`) in streaming mode, yielding tokens token-by-token to the WebSocket client.

---

### 1.6 GitHub Data Collection

**Source:** PyGithub library (REST API wrapper). Three concurrent async-wrapped calls:

1. `fetch_user_commit_hours(username, days=90)` — iterates over user-owned repos, fetches commits authored by username since `now - 90d`, collects `commit.commit.author.date.hour`.
2. `fetch_pr_metrics(username, days=90)` — collects PRs: count, avg close time (hours), after-hours ratio (PRs created 20:00–07:00).
3. `fetch_collaboration_index(username, days=90)` — counts PR review comments authored by username (each comment = +2 points, capped at 100).

**Rate limit budget:** 5000 pts/hr per token. One full user analysis costs approximately 15–30 API points.

---

## Part 2 — Paper Structure: Section-by-Section Writing Guide

### Section 1: Abstract (~250 words)

**What to write:**  
One sentence: problem statement. One sentence: gap in existing work. Two sentences: proposed approach (what the system does technically — circular K-Means, adaptive testing, Monte Carlo). One sentence: key results (if evaluation data is available) or claimed contributions. One sentence: significance.

**Key phrases to include:**  
- "behavioral telemetry from version control systems"  
- "circular-coordinate K-Means clustering for chronotype classification"  
- "eight-dimensional weighted compatibility scoring"  
- "Computerized Adaptive Testing (CAT)"  
- "Monte Carlo candidate simulation"

**Do NOT say:** "We present a revolutionary system." Keep it factual and precise.

---

### Section 2: Introduction (~1.5 pages)

**Paragraph 1 — Problem:**  
Software team effectiveness is not determined by individual technical skill alone; it depends substantially on behavioral alignment in work rhythms, communication styles, and decision-making approaches [CITE: Herbsleb & Grinter 1999; De Choudhury et al. 2010]. Engineering teams that fail to ship on time or produce defect-heavy software frequently exhibit patterns of chronotype mismatch, conflicting communication densities, and unresolved leadership ambiguity [CITE: Tamburri et al. 2019; Catolino et al. 2019].

**Paragraph 2 — Gap in existing tools:**  
Current approaches to team assessment fall into two categories: (a) static psychometric instruments such as Myers-Briggs Type Indicator (MBTI) [CITE: Myers & Briggs 1943] and DiSC [CITE: Marston 1928], which rely entirely on self-report and produce a single-point-in-time label disconnected from observed work behavior; and (b) project management analytics tools (Jira, GitHub Insights) that capture activity metrics but do not produce actionable behavioral compatibility scores [CITE: Dingsøyr et al. 2012]. No published system combines behavioral telemetry from version control with adaptive psychometric profiling to produce a pairwise team compatibility score.

**Paragraph 3 — This work:**  
We present GitSyntropy, a multi-agent system that derives team compatibility scores from two complementary signal sources: (1) behavioral telemetry extracted from GitHub commit and pull-request history, and (2) responses to an eight-item Computerized Adaptive Testing (CAT) assessment. The system applies K-Means clustering in circular coordinate space to classify developer chronotypes from commit timestamp distributions, fuses these signals with a weighted eight-dimensional scoring model, and uses Monte Carlo simulation to predict the impact of candidate hires on team compatibility.

**Paragraph 4 — Contributions (numbered list):**
1. A **circular-coordinate K-Means algorithm** for chronotype classification from VCS commit timestamps that correctly handles the midnight hour boundary.
2. A **weighted eight-dimensional team compatibility engine** (max 36 points) adapting the Ashtakoot scoring framework to software team behavioral dimensions, with confidence-aware imputation for missing data.
3. A **greedy information-maximizing CAT algorithm** for psychometric profiling that achieves early stopping in 5 of 8 questions when high-weight dimensions are covered.
4. A **Monte Carlo candidate simulation** that produces an optimal hire profile and improvement distribution over 1,000 iterations.
5. A **full-stack implementation** with a LangGraph multi-agent pipeline, WebSocket-streamed synthesis via a large language model, and an open-source reference codebase.

**Paragraph 5 — Paper organization.**

**Required citations for this section:**
- Herbsleb, J. D., & Grinter, R. E. (1999). Splitting the organization and integrating the code: Conway's law revisited. ICSE.
- Tamburri, D. A., Kruchten, P., Lago, P., & van Vliet, H. (2019). What is software organizational debt? JSS.
- Catolino, G., Palomba, F., Zanoni, M., Ferme, V., De Lucia, A., & Zaidman, A. (2019). Understanding the relationship between anti-patterns and community smells in software projects. ICSME.
- Myers, I. B., & Briggs, K. C. (1943). Myers-Briggs Type Indicator. CPP.
- Marston, W. M. (1928). Emotions of Normal People. Kegan Paul.
- Dingsøyr, T., Nerur, S., Balijepally, V., & Moe, N. B. (2012). A decade of agile methodologies: Towards explaining agile software development. JSS.

---

### Section 3: Background and Related Work (~1.5 pages)

**3.1 Developer Behavioral Analytics from VCS**  
Git and GitHub commit history have been mined extensively for productivity signals [CITE: Kalliamvakou et al. 2014 MSR — "The Promises and Perils of Mining GitHub"], work timing [CITE: Claes et al. 2018 — "Do Programmers Work at Night or During Weekends?", MSR], and collaboration patterns [CITE: Bird et al. 2009 — "Promises and Perils of Mining Git"]. Chronotype inference specifically from commit timestamps was explored by Claes et al. (2018), who studied 1,000 GitHub users and found significant night-owl and morning-bird populations. Our work extends this by applying circular-space clustering rather than naive histogram peak detection.

**3.2 Chronotype and Work Rhythm Science**  
Circadian chronotype (the biological tendency toward morning or evening activity) is measured clinically via the Morningness-Eveningness Questionnaire (MEQ) [CITE: Horne & Östberg 1976] and influences individual productivity windows [CITE: Gunia et al. 2014 — "The Marine Layer: When people work best and what it means for organizations", Journal of Applied Psychology]. Team chronotype mismatch creates synchronous meeting conflicts and asynchronous handoff delays. Handling the circular nature of clock time requires circular statistics [CITE: Fisher 1993 — "Statistical Analysis of Circular Data", Cambridge University Press].

**3.3 Psychometric Profiling for Teams**  
Self-report personality instruments (MBTI, OCEAN/Big Five [CITE: McCrae & Costa 1987], DiSC) are widely used in team building but have been criticized for low test-retest reliability [CITE: Pittenger 1993 — "Measuring the MBTI and Coming Up Short"] and poor predictive validity for team performance [CITE: Halfhill et al. 2005 — "Group Personality Composition and Group Effectiveness", Small Group Research]. We use a purpose-built 8-item instrument aligned directly to the scoring dimensions rather than mapping general-purpose personality traits.

**3.4 Computerized Adaptive Testing**  
CAT systems dynamically select the next test item to maximize information gain given the current ability estimate, typically using Item Response Theory (IRT) [CITE: van der Linden & Glas 2000 — "Computerized Adaptive Testing", Kluwer]. For short fixed-bank instruments, greedy weight-maximization provides a tractable approximation that reduces administration length while maintaining score coverage [CITE: Wainer et al. 2000 — "Computerized Adaptive Testing: A Primer"]. 

**3.5 Team Composition Optimization**  
Belbin's team roles [CITE: Belbin 1981] proposed complementary role assignments. Recent computational approaches use integer programming [CITE: Fitzpatrick & Askin 2005 — "Forming Effective Worker Teams with Multi-Dimensional Skill Requirements", Computers & IE] and simulation [CITE: Lappas et al. 2009 — "Finding a Team of Experts in Social Networks", KDD] for team formation. Monte Carlo methods for hire-impact prediction are not, to our knowledge, described in the literature on software team composition.

**3.6 The Ashtakoot Framework**  
Ashtakoot ("eight attributes") is a classical Hindu astrological compatibility scoring system with a total of 36 points distributed across 8 weighted dimensions [CITE: Parashara's Brihat Parashara Hora Shastra, ~800 CE; modern reference: Charak 1994 — "Subtleties of Medical Astrology"]. We extract only its weight structure (1, 2, 3, 4, 5, 6, 7, 8 points) and map it to empirically motivated software-team behavioral dimensions. The astronomical interpretation is discarded entirely; only the differential weighting principle is retained.  
**Note to authors:** Frame this carefully — you are using the numerical weight structure as a design choice, not endorsing astrological interpretation. The weight structure creates a natural ordinal priority: chronotype sync (8 pts) is weighted as the most impactful dimension, reflecting research showing that schedule misalignment is the primary friction source in distributed/hybrid teams [CITE: Tamburri et al. 2019; Holmström et al. 2006 — "Global Virtual Teams and the Role of Coordination"].

---

### Section 4: System Design (~2 pages)

**4.1 Architecture Overview**  
Present the pipeline diagram (Figure 1):
```
GitHub REST API
       ↓
GitHub Analyst Agent (PyGithub + Circular K-Means)
       ↓
Psychometric Profiler (CAT Engine + Likert Score Mapping)
       ↓
Compatibility Engine (8-dim weighted similarity)
       ↓
[Optional] Monte Carlo Simulator (candidate search)
       ↓
Synthesis Agent (Claude claude-sonnet-4-6, streaming)
       ↓
WebSocket → Astro/React Frontend
```
Implementation: FastAPI (async Python), SQLAlchemy + asyncpg, Supabase (PostgreSQL), LangGraph for DAG orchestration, Anthropic Claude for narrative synthesis, Astro + React frontend with recharts visualizations.

**4.2 GitHub Data Ingestion**  
Describe the three async concurrent calls (commit hours, PR metrics, collaboration index). State the 90-day lookback window. Note the circular-coordinate preprocessing step.

**4.3 Chronotype Classification Module**  
Present Algorithm 1 in LaTeX pseudocode form, with the full pipeline from raw hours to label+confidence. Include the entropy-based "flexible" fallback and the <10-commit fallback. Include equations for the circular coordinate transform and the atan2 inverse.

**4.4 Psychometric Assessment (CAT)**  
Present the 8-item question bank (Table 2). Present Algorithm 2: greedy weight-maximization with early-stop criterion. Note that this is a first-principles approximation to IRT-based CAT suited for a fixed 8-item bank.

**4.5 Compatibility Engine**  
Present the scoring formula (Equation 1). Present the confidence metric. Present the level thresholds (Table 3). Present the special chronotype-sync risk flag. Explain the neutral imputation for missing dimensions.

**4.6 Monte Carlo Candidate Simulation**  
Present Algorithm 3. Explain the biased sampling heuristic for weak dimensions. Explain the deterministic seed for reproducibility. Explain the output statistics.

**4.7 LLM Synthesis**  
Describe the structured prompt format fed to Claude. Note the streaming architecture: tokens arrive token-by-token from the Anthropic streaming API and are forwarded over WebSocket to the client.

---

### Section 5: Evaluation (~2 pages)

**IMPORTANT:** This section requires empirical data that must be collected before submission. The following sub-sections describe what experiments to run. Do not invent numbers.

**5.1 Chronotype Detection Accuracy**

*Experiment:* Recruit a set of GitHub users (target: n ≥ 50) who also completed a validated chronotype self-report instrument (MEQ or Munich Chronotype Questionnaire, MCTQ [CITE: Roenneberg et al. 2003 — "Life between Clocks: Daily Temporal Patterns of Human Chronotypes", Journal of Biological Rhythms]). Run the circular K-Means algorithm on their commit history. Compare predicted label to self-reported label.

*Metrics:* Accuracy, macro F1, confusion matrix. Report confidence stratified by sample size.

*Baseline:* Naive peak-hour detection without circular coordinate transform. Show that the circular method improves classification near the midnight boundary.

*Visualization (Figure 2):* Confusion matrix heatmap. Confidence vs. accuracy scatter plot.

**5.2 Compatibility Score Validity**

*Experiment:* Collect compatibility scores for known developer pairs. Obtain a proxy ground truth: peer-review survey scores (e.g., "how effectively do you collaborate with this person, 1–5?"), or retrospective team effectiveness ratings.

*Analysis:* Pearson/Spearman correlation between GitSyntropy compatibility score and peer rating. If n is small, report exact 95% CI via bootstrap resampling [CITE: Efron & Hastie 2016 — "Computer Age Statistical Inference"].

*Visualization (Figure 3):* Scatter plot of compatibility score vs. peer rating with regression line and CI band.

**5.3 CAT Efficiency**

*Experiment:* On the question bank, simulate full 8-question completion for all possible response permutations (5^8 = 390,625 combinations). For each, record when the early-stop criterion triggers. Report the distribution of early-stop positions.

*Metrics:* Mean questions answered before early stop, fraction of completions where early stop triggers, Pearson correlation between full-8-answer score and early-stop-truncated score.

*Visualization (Figure 4):* Histogram of early-stop positions (1–8 questions). Scatter plot: full score vs. truncated score.

**5.4 Monte Carlo Convergence**

*Experiment:* Run the simulation at n = {100, 200, 500, 1000, 2000, 5000}. Measure: (a) variance of `mean_improvement` across 10 independent runs with different random seeds; (b) Euclidean distance of `optimal_profile` from the 5000-iteration reference.

*Visualization (Figure 5):* Line plot: variance of improvement estimate vs. n_iterations. Line plot: optimal profile distance vs. n_iterations. Show that convergence plateaus at n=1000.

**5.5 System Performance**

*Measurements:*  
- End-to-end pipeline latency (p50, p95) from WebSocket open to first synthesis token.
- GitHub API call latency breakdown (commit fetch, PR fetch, collab index) — 90-day window.
- Database query time for pairwise team scoring (scale: 2, 5, 10 members).

*Table (Table 4):* Latency breakdown by pipeline stage.

---

### Section 6: Discussion (~0.75 pages)

**6.1 Limitations**

1. **Ground truth scarcity:** Validated chronotype labels for GitHub users are difficult to obtain at scale. The MEQ has its own limitations as a gold standard.
2. **Assessment self-report bias:** The 8-item psychometric questionnaire is still subject to social-desirability bias, despite being designed around behavioral scenarios rather than trait adjectives.
3. **Circular K-Means assumption:** Assumes commit activity is unimodal (single dominant cluster). Developers with genuinely bimodal schedules (e.g., early morning + late night) may be misclassified.
4. **Score scale calibration:** The Ashtakoot weight structure (1–8) was adapted, not derived from empirical data. The weights reflect a design hypothesis, not a validated factor loading.
5. **LLM synthesis variability:** Claude's narrative synthesis is non-deterministic. The factual layer (scores, dimensions) is stable; the narrative framing varies across runs.
6. **GitHub data completeness:** Private repositories are inaccessible. Developers who commit primarily to private repos will have sparse chronotype data, producing low-confidence classifications.

**6.2 Future Work**

1. Validate chronotype labels against MEQ at scale (n ≥ 200 GitHub users).
2. Calibrate dimension weights empirically via a regression study linking GitSyntropy scores to retrospective team performance outcomes.
3. Replace greedy CAT with a proper IRT-based adaptive algorithm for a larger question bank.
4. Integrate real-time GitHub webhooks for continuous (not point-in-time) compatibility monitoring.
5. Privacy analysis: commit timestamps reveal work schedules — study user consent and de-identification requirements.

---

### Section 7: Conclusion (~0.5 pages)

Restate the problem: predicting software team behavioral compatibility before friction occurs. Restate the approach: circular K-Means chronotype detection + 8-dimensional weighted scoring + CAT + Monte Carlo simulation + LLM synthesis. State the main contribution clearly. Note that the system is open source and available for replication. End with the broader implication: behavioral telemetry from public version control repositories is an underutilized signal for team management decisions.

---

### References

**EVERY claim in the paper must be cited. Below is the working bibliography. Add DOIs and page numbers during final editing.**

| Ref | Citation | Where Used |
|---|---|---|
| [1] | Herbsleb & Grinter (1999). Splitting the organization and integrating the code. ICSE. | §2, §3 |
| [2] | Kalliamvakou et al. (2014). The Promises and Perils of Mining GitHub. MSR. | §3.1 |
| [3] | Claes et al. (2018). Do Programmers Work at Night or During Weekends? MSR. | §3.1, §5.1 |
| [4] | Bird et al. (2009). Promises and Perils of Mining Git. MSR. | §3.1 |
| [5] | Horne & Östberg (1976). A self-assessment questionnaire to determine morningness-eveningness. Int J Chronobiol. | §3.2, §5.1 |
| [6] | Gunia et al. (2014). The Marine Layer: When people work best. J Applied Psychology. | §3.2 |
| [7] | Fisher (1993). Statistical Analysis of Circular Data. Cambridge University Press. | §3.2 |
| [8] | McCrae & Costa (1987). Validation of the five-factor model of personality. J Personality Social Psychology. | §3.3 |
| [9] | Pittenger (1993). Measuring the MBTI and Coming Up Short. J Career Planning. | §3.3 |
| [10] | Halfhill et al. (2005). Group Personality Composition and Group Effectiveness. Small Group Research. | §3.3 |
| [11] | van der Linden & Glas (2000). Computerized Adaptive Testing: Theory and Practice. Kluwer. | §3.4 |
| [12] | Wainer et al. (2000). Computerized Adaptive Testing: A Primer. 2nd ed. Erlbaum. | §3.4 |
| [13] | Belbin (1981). Management Teams: Why They Succeed or Fail. Heinemann. | §3.5 |
| [14] | Fitzpatrick & Askin (2005). Forming Effective Worker Teams. Computers & IE. | §3.5 |
| [15] | Lappas et al. (2009). Finding a Team of Experts in Social Networks. KDD. | §3.5 |
| [16] | Tamburri et al. (2019). What is software organizational debt? JSS. | §1, §3.6 |
| [17] | Roenneberg et al. (2003). Life between Clocks: Daily Temporal Patterns of Human Chronotypes. J Biological Rhythms. | §5.1 |
| [18] | Efron & Hastie (2016). Computer Age Statistical Inference. Cambridge. | §5.2 |
| [19] | Dingsøyr et al. (2012). A decade of agile methodologies. JSS. | §2 |
| [20] | Holmström et al. (2006). Global Virtual Teams and the Role of Coordination. IEEE Software. | §3.6 |
| [21] | Marston (1928). Emotions of Normal People. Kegan Paul. | §2 |
| [22] | Catolino et al. (2019). Understanding the relationship between anti-patterns and community smells. ICSME. | §1 |
| [23] | Myers & Briggs (1943). Myers-Briggs Type Indicator. CPP. | §2 |

---

## Part 3 — Figures Specification

All figures must be generated from real data or clearly labeled as "illustrative example" if using synthetic data.

### Figure 1 — System Architecture Diagram
**Type:** Block diagram (draw in TikZ or Graphviz, export as PDF).  
**Content:** The 5-stage pipeline from §4.1. Include data flow arrows, label each stage with: (a) stage name, (b) algorithm/model used, (c) input/output data type.  
**Caption:** "The GitSyntropy multi-agent pipeline. Boxes denote processing stages; arrows denote data flow. The candidate simulation stage (dashed border) is optional."

### Figure 2 — Chronotype Confusion Matrix + Confidence Plot
**Type:** Two-panel figure.  
Left panel: 4×4 confusion matrix heatmap (lark/daytime/evening/owl) — actual vs. predicted. Colormap: Blues.  
Right panel: Confidence score distribution (box plot or violin) grouped by whether the prediction was correct or incorrect.  
**Data source:** User study (n ≥ 50) or synthetic benchmark if user study not ready.  
**Caption:** "Chronotype classification accuracy. Left: confusion matrix against self-reported MEQ labels. Right: confidence score distribution by correctness — higher confidence correlates with correct classification."

### Figure 3 — Compatibility Score vs. Peer Rating
**Type:** Scatter plot with regression line.  
X-axis: GitSyntropy compatibility score (0–36).  
Y-axis: Peer-reported collaboration quality (1–5).  
Color points by team (if multiple teams).  
Include: Pearson r, 95% CI, p-value in the figure.  
**Caption:** "GitSyntropy compatibility score vs. peer-reported collaboration quality (n = X developer pairs). The score correlates positively with perceived collaboration effectiveness (r = X, p < 0.05)."

### Figure 4 — CAT Early-Stop Analysis
**Type:** Two-panel figure.  
Left panel: Histogram of number of questions answered before early stop (x = 1..8, y = frequency across simulated response patterns).  
Right panel: Scatter plot, x = full-8-item score, y = early-stopped score. Reference line y=x. Color by number of questions answered.  
**Caption:** "CAT early-stop analysis over all 5^8 = 390,625 simulated response patterns. Left: most assessments stop at 5 questions. Right: early-stopped scores closely approximate full-assessment scores."

### Figure 5 — Monte Carlo Convergence
**Type:** Two-panel line plot.  
Left panel: x = n_iterations, y = variance of mean_improvement estimate (10 independent seeds). Show plateau.  
Right panel: x = n_iterations, y = Euclidean distance of optimal_profile from 5000-iteration reference.  
**Caption:** "Monte Carlo simulation convergence. Both improvement estimate variance and optimal profile error stabilize at n ≈ 1000 iterations, justifying the default iteration count."

### Figure 6 (Optional) — Dashboard Screenshot
A labeled screenshot of the frontend showing RadarChart, compatibility breakdown, and streaming synthesis. For the camera-ready version only. Must show realistic data, not placeholder text.

---

## Part 4 — Statistical Analysis Checklist

Before submitting, verify these statistical requirements are met:

- [ ] All reported means accompanied by standard deviation or 95% CI.
- [ ] Sample size (n) stated for every experiment.
- [ ] Normality check (Shapiro-Wilk) before applying parametric tests; use Spearman if non-normal.
- [ ] Effect sizes reported (Cohen's d or r) in addition to p-values.
- [ ] Bootstrap resampling (B ≥ 10,000) for CIs on small samples (n < 30).
- [ ] Monte Carlo results: report both mean and percentile statistics (p25, p75) — not just the best case.
- [ ] Baseline comparison for chronotype detection (naive peak vs. circular K-Means).
- [ ] No result stated without a corresponding table or figure in the paper.

---

## Part 5 — Writing Guidelines (Anti-AI-Detection Notes)

The paper must read as scholarly human writing. Specific instructions:

1. **Never use list-heavy prose in narrative sections.** The introduction, related work, and discussion should be full paragraphs — not bullet lists.
2. **Vary sentence length.** Mix short declarative sentences with longer compound ones. Do not write all sentences at the same length.
3. **Use hedged language appropriately.** "Our results suggest..." rather than "Our results prove...". "To the best of our knowledge..." for novelty claims.
4. **Cite early and specifically.** Every factual claim must have a citation in the same sentence — not at the end of a paragraph. Specific author-year references (e.g., "Claes et al. [3] found...") read more natural than bare number citations.
5. **Use passive voice selectively.** Passive is appropriate for experimental procedure sections ("Commits were collected over a 90-day window"). Active is better for contribution statements ("We apply circular-coordinate K-Means...").
6. **Avoid AI-characteristic phrases:** "delve into", "it is important to note", "furthermore", "in conclusion", "a nuanced approach", "comprehensive overview", "multifaceted".
7. **Write figures into the text.** Every figure must be explicitly discussed in the text ("As shown in Figure 2...") — do not leave figures to speak for themselves.
8. **Acknowledge limitations directly.** Do not soften or omit limitations. Reviewers penalize papers that oversell.
9. **Use exact numbers.** "The total weight sums to 36 points (1+2+3+4+5+6+7+8)" rather than "the total weight is a fixed constant".
10. **Write the abstract last.** After all sections are written.

---

## Part 6 — Patent Strategy (Parallel Track)

### Provisional Patent Application (PPA) in India

**Filing authority:** Indian Patent Office (IPO), under the Patents Act 1970, Section 9.  
**Cost (individual/startup):** ₹1,600 (Form-2 provisional) + ₹200 search fee = ~₹1,800 total.  
**What to include in the provisional:**
1. Title: "A Method and System for Software Team Compatibility Assessment Using Behavioral Telemetry and Adaptive Psychometric Profiling"
2. Background section: describe the problem (team friction prediction).
3. Summary of invention: three claims as described below.
4. Brief description of drawings: pipeline block diagram.
5. **Do not include full claims** in the provisional — those go in the complete specification.

**Three core process patent claims to draft:**

1. **Claim 1 — Chronotype Detection:**  
"A computer-implemented method for classifying work chronotype of a software developer comprising: extracting a plurality of commit timestamps from a version control repository associated with the developer over a predefined temporal window; transforming each timestamp hour h into a two-dimensional circular coordinate (cos(2πh/24), sin(2πh/24)); applying unsupervised cluster analysis to said circular coordinates to identify a dominant activity cluster; deriving a peak hour from the centroid of said dominant cluster via inverse trigonometric transformation; classifying the developer into one of a plurality of chronotype categories based on said peak hour; and computing a confidence score as the fraction of timestamps belonging to said dominant cluster."

2. **Claim 2 — Team Compatibility Scoring:**  
"A computer-implemented method for quantifying behavioral compatibility between members of a software engineering team comprising: acquiring a plurality of behavioral dimension scores for each team member from at least one of (a) a psychometric assessment instrument and (b) behavioral telemetry derived from version control repository activity; computing for each of a plurality of weighted behavioral dimensions a pairwise similarity score using a normalized absolute-difference formula; aggregating said similarity scores using dimension-specific weights to produce a composite team compatibility score; and generating risk flags for dimensions where the pairwise score falls below a predefined threshold relative to the dimension weight."

3. **Claim 3 — Monte Carlo Candidate Simulation:**  
"A computer-implemented method for identifying an optimal behavioral profile for a candidate addition to a software engineering team comprising: computing a baseline mean pairwise compatibility score for the existing team members; identifying dimensions in which the team mean score falls below a predefined fraction of the maximum possible dimension score; for each of a plurality of iterations, sampling a candidate behavioral profile vector with a sampling distribution biased toward the identified low-scoring dimensions; computing the mean pairwise compatibility of the sampled candidate with existing team members; and returning the candidate profile that maximizes the improvement in mean pairwise compatibility over the baseline score."

**After conference acceptance:** file complete specification (Form-2 complete) converting the provisional. Include the published paper as prior art disclosure by the applicant.

---

## Part 7 — Action Items Before Submission

These items must be completed before a paper can be submitted:

### Data Collection (Required for Evaluation Section)
- [ ] Recruit ≥ 50 GitHub users who consent to having their commit history analyzed + who complete MEQ self-report.
- [ ] Design and administer peer collaboration rating survey for ≥ 5 existing developer pairs.
- [ ] Run the CAT simulation over all 5^8 response combinations (can be fully automated in Python).
- [ ] Run Monte Carlo convergence experiment at varying iteration counts (can be automated).

### Writing
- [ ] Draft Section 1 (Introduction) — ~1.5 pages.
- [ ] Draft Section 2 (Background) — ~1.5 pages.
- [ ] Draft Section 3 (System Design) — ~2 pages with Algorithm 1/2/3 pseudocode.
- [ ] Draft Section 4 (Evaluation) — fill after data collection.
- [ ] Draft Section 5 (Discussion + Conclusion) — ~1.25 pages.
- [ ] Write Abstract last.

### Figures
- [ ] Figure 1: Architecture diagram (TikZ recommended for IEEE format).
- [ ] Figures 2–5: Generate after data collection.

### Logistics
- [ ] File India Provisional Patent Application (PPA) before submitting to conference.
- [ ] Check MSR 2027 call for papers (typically announced August–September 2026).
- [ ] Register on HotCRP / EasyChair per conference requirement.
- [ ] Get institutional affiliation — check if university affiliation is needed for the venue.

---

## Part 8 — Complete Context Dump for LLM Assistants

**If you are an LLM being asked to write a section of this paper, read this section carefully before generating any text.**

### What this system does (plain language)

GitSyntropy takes a list of GitHub usernames (a software team), fetches their commit history from GitHub, runs a machine learning algorithm to detect when each person tends to work (their "chronotype"), asks each person 5–8 multiple-choice questions about their work style, then computes a compatibility score between every pair of team members across 8 behavioral dimensions. The score is out of 36. It also runs a simulation to find out what kind of person, if hired, would most improve the team's score.

### What this system does NOT do

- It does not analyze code quality, skill level, or language expertise.
- It does not use any astrological or spiritual methodology — the 8 dimensions and their weight structure (1,2,3,4,5,6,7,8) are borrowed from a traditional framework but the content is entirely behavioral and empirically grounded.
- It does not use any LLM for scoring — Claude is used only for generating a narrative report after the numerical scores are computed.
- It does not make hiring decisions — it produces a profile of the "optimal complement" which a human hiring manager interprets.
- It does not have validated ground truth data yet — this is an ongoing project. Do not claim empirical validation unless Section 5 data has been collected and you have been given the actual numbers.

### Technical facts you must not hallucinate

- The total compatibility score is out of **36** (not 100, not 10, not 40).
- The 8 weights are exactly **1, 2, 3, 4, 5, 6, 7, 8** in ascending order by dimension.
- K-Means uses **k=min(3, unique_hours)**, **random_state=42**, **n_init=10**.
- The entropy threshold for "flexible" is **0.92** (of max entropy).
- The early-stop criterion requires **≥4 questions answered**, **≥70% weight covered**, and **no unanswered question with weight ≥4**.
- Monte Carlo uses **seed=42**, default **1000 iterations**.
- Weak-dimension sampling range: **Uniform(0.5×weight, 1.0×weight)**.
- The compatibility level thresholds are: **≥28 excellent, ≥20 good, ≥12 fair, <12 poor**.
- The GitHub lookback window is **90 days** by default.
- Rate limit budget: **~15–30 API points** per full user analysis.
- Backend: **FastAPI + SQLAlchemy + asyncpg + Supabase (PostgreSQL)**.
- Frontend: **Astro + React + Tailwind + recharts + Framer Motion**.
- Orchestration: **LangGraph** (DAG with async node functions).
- LLM: **Anthropic claude-sonnet-4-6**, streaming, max 600 tokens for synthesis.

### Dimension-to-question mapping (exact)

| Question ID | Question Text | Left → Right | Dimension Key | Weight |
|---|---|---|---|---|
| q1 | Decision style in uncertainty | Intuitive → Analytical | varna_alignment | 1 |
| q2 | Preferred delivery rhythm | Steady → Bursty | vashya_influence | 2 |
| q3 | Conflict handling pattern | Direct → Diplomatic | tara_resilience | 3 |
| q4 | Team interaction mode | Independent → Collaborative | yoni_workstyle | 4 |
| q5 | Context switching tolerance | Low → High | graha_maitri_cognition | 5 |
| q6 | Communication density | Concise → Detailed | gana_temperament | 6 |
| q7 | Experimentation appetite | Conservative → Exploratory | bhakoot_strategy | 7 |
| q8 | Working-hour preference | Early → Late | nadi_chronotype_sync | 8 |

### What the paper claims as novel (and what it must not over-claim)

**Claimed novel:**
1. Application of circular-coordinate K-Means to VCS commit timestamps for chronotype detection (prior work used histogram peaks without circular statistics).
2. Repurposing the Ashtakoot weight structure for software team behavioral dimensions.
3. CAT early-stop algorithm for the specific 8-item work-style assessment.
4. Monte Carlo candidate simulation for hire-impact prediction in software teams.
5. Integration of VCS behavioral telemetry + adaptive psychometric profiling into a single compatibility score.

**Not claimed novel (must not say "we are the first to"):**
- Behavioral analytics from GitHub (Kalliamvakou 2014, Claes 2018 are prior work).
- CAT as a methodology (van der Linden 2000 is prior work).
- Monte Carlo simulation in general.
- LLM-generated narratives.
- Team formation algorithms (Lappas 2009 and others are prior work).

---

*End of Research Paper Plan — GitSyntropy v1.0 — 2026-04-12*
