# GitSyntropy — Paper Writing Continuation Prompt
## Paste this entire prompt at the start of a new chat session

---

## Context

I am writing a 6-page IEEE conference paper for **WorldSUAS 2026 (IEEE World Skill Conference on Universal Data Analytics and Sciences)** about a system called **GitSyntropy**.

The complete project is at: `G:\synced-pc\1_Work\projects\GitSyntropy\`

All data collection and analysis is **complete**. Results are at `scripts/results/`. The paper plan is at `docs/RESEARCH_PAPER_PLAN.md`. There is a raw draft at `scripts/GitSyntropy_Paper_raw_draft1.docx` (binary, unreadable by tools — treat as placeholder).

---

## What GitSyntropy Does (no hallucination zone)

GitSyntropy predicts software team behavioral compatibility using two data sources:
1. GitHub commit timestamps → **chronotype classification** (circular K-Means)
2. 8-item adaptive psychometric assessment → **behavioral profile**

It outputs a **compatibility score out of 36** across 8 weighted dimensions (weights 1–8, total 36), runs **Monte Carlo simulation (1000 iter)** to find optimal hire profiles, and uses **Claude claude-sonnet-4-6** for streaming narrative synthesis.

---

## All Hard Numbers (do not invent any others)

### Real Dataset
- **n = 46 real GitHub developer profiles** (90-day lookback)
- **10,886 total commits** analysed
- Mean commits/developer: 236.7 (range 50–931)
- Profiles include: gvanrossum, rgommers, antfu, sindresorhus, dtolnay, mitsuhiko, nikomatsakis, tianon, thockin, potiuk, emilio, simonw, etc.

### Chronotype Distribution (real data, n=46)
| Chronotype | Count | % |
|---|---|---|
| Lark (early) | 6 | 13.0% |
| Daytime | 19 | 41.3% |
| Evening | 9 | 19.6% |
| Owl (night) | 8 | 17.4% |
| Flexible | 4 | 8.7% |
- Mean prediction confidence: 0.445

### CAT Algorithm (all 390,625 patterns simulated)
- Early-stop rate: **100%** of patterns trigger early stop
- Mean questions answered: **5.0 / 8** (37.5% reduction)
- Score correlation full vs truncated: **r = 0.965** (p < 0.001)

### Monte Carlo Convergence (10 seeds per iteration count)
| n_iterations | var(improvement) | profile_distance |
|---|---|---|
| 100 | 0.016544 | 1.841 |
| 200 | 0.011880 | 1.835 |
| 500 | 0.007290 | 1.425 |
| 1000 | 0.004584 | 1.216 |
| 2000 | 0.001230 | 1.038 |
| 5000 | 0.000760 | 1.014 |
- Variance drops **3.6×** from n=100 to n=1000

### Compatibility Model (500 random pairs)
- Mean score (random pairs): **25.13 / 36**
- Chronotype-aligned pairs: **35.74 / 36**
- Chronotype-mismatched pairs: **24.82 / 36**
- t-test: **p < 0.001**, Cohen's d = **3.71**

### Ashtakoot Dimension Weights (exact, total = 36)
varna_alignment=1, vashya_influence=2, tara_resilience=3, yoni_workstyle=4,
graha_maitri_cognition=5, gana_temperament=6, bhakoot_strategy=7, nadi_chronotype_sync=8

### English labels (NEVER use Vedic names in paper):
- varna → Innovation Drive, vashya → Leadership Orientation, tara → Team Resilience
- yoni → Work Style, graha_maitri → Decision Style, gana → Risk Tolerance
- bhakoot → Stress Response, nadi → Chronotype Sync

### Compatibility Thresholds: ≥28 excellent, ≥20 good, ≥12 fair, <12 poor

---

## Figures Already Generated (all at scripts/results/)

| File | Description | Status |
|---|---|---|
| fig2_crossval_and_distribution.pdf | 3-panel: SO cross-val matrix + commit hour histogram + chronotype distribution bar | REAL DATA (histogram + distribution from n=46) |
| fig2_chronotype_confusion.pdf | Confusion matrix + confidence violin (synthetic n=80, labeled as such) | SYNTHETIC |
| fig3_compatibility_model.pdf | Score distribution + chronotype mismatch impact | SYNTHETIC |
| fig4_cat_early_stop.pdf | Stop-position histogram + score correlation scatter | ALGORITHMIC (exact) |
| fig5_monte_carlo_convergence.pdf | Variance + profile distance vs iterations | ALGORITHMIC (exact) |
| fig_dimensions_weights.pdf | Horizontal bar chart of 8 dimension weights | EXACT |
| table1_chronotype_per_user.csv | Per-user chronotype, confidence, peak hour | REAL |
| table2_chronotype_distribution.csv | Chronotype counts + % | REAL |
| paper_stats_master.json | All numbers above in JSON | REAL |

**For the paper: use fig2_crossval_and_distribution (real data) as the primary Figure 2. Use fig4 and fig5 as main algorithmic figures. The synthetic confusion matrix can be in the paper labeled "Simulated validation (n=80)" pending real MEQ data.**

---

## Survey Status
- Full 19-item MEQ: `scripts/02_meq_survey.py` — too hard to distribute, barely any responses
- 5-item rMEQ: `scripts/02b_rmeq_survey.py` — circulated via Google Form, got ~10-12 responses (below 30 minimum for full validation section)
- **Decision: reframe Section V-A as "preliminary validation + behavioral cross-validation" rather than a full accuracy study**

---

## What Needs to Be Done (tasks for next session)

### PRIORITY 1 — Write the paper
The paper sections to write (6 pages, IEEEtran, double-column):

**Abstract** (150 words) — write last
**Section I: Introduction** (~0.7 pages)
- Problem: team friction prediction before it happens
- Gap: MBTI/DiSC are static self-report; GitHub tools lack behavioral compatibility
- Contributions: 4 numbered bullets (circular K-Means, 8-dim scoring, CAT, Monte Carlo)

**Section II: Related Work** (~0.7 pages)
- Cite: Kalliamvakou 2014 (MSR), Claes 2018 (commit timing), Horne & Östberg 1976 (MEQ),
  van der Linden 2000 (CAT), Lappas 2009 (team formation), Belbin 1981, Halfhill 2005

**Section III: System Design** (~1.5 pages)
- Fig 1: architecture block diagram (needs to be made in draw.io or TikZ)
- Algorithm 1: Circular K-Means chronotype (pseudocode)
- Algorithm 2: CAT greedy selection (pseudocode)
- Table: 8 dimensions + weights
- Equation: compatibility formula

**Section IV: Experiments** (~2 pages)
- IV-A: Dataset (n=46, 10,886 commits, Table of stats)
- IV-B: Chronotype distribution (Fig 2 real-data panel — commit histogram + distribution)
- IV-C: CAT efficiency (Fig 4 — 100% early stop, mean 5.0 questions, r=0.965)
- IV-D: Monte Carlo convergence (Fig 5 — stabilises at n=1000)
- IV-E: Compatibility model (Fig 3 — p<0.001, d=3.71 for chronotype alignment)

**Section V: Discussion** (~0.4 pages)
- Limitations: UTC timestamps (bias for non-UTC devs), no external team outcome data,
  synthetic validation pending real MEQ study, SO cross-validation inconclusive

**Section VI: Conclusion** (~0.2 pages)

**References** (cite all from docs/RESEARCH_PAPER_PLAN.md reference table)

### PRIORITY 2 — Architecture Figure (Fig 1)
Create a clean block diagram of the 5-stage pipeline:
```
GitHub REST API → GitHub Analyst (Circular K-Means)
               → Psychometric Profiler (CAT)
               → Compatibility Engine (8-dim weighted)
               → [Monte Carlo Simulator]
               → Synthesis Agent (Claude claude-sonnet-4-6)
               → WebSocket → Astro/React Frontend
```
Can use matplotlib, graphviz, or draw.io. Save as fig1_architecture.pdf

### PRIORITY 3 — rMEQ data
If the ~10-12 rMEQ responses are available in `scripts/data/rmeq_responses.csv`:
- Run `python scripts/02b_rmeq_survey.py process`
- Add as a "preliminary validation" paragraph in Section IV-A
- n=10-12 is too small for confusion matrix but OK for anecdotal support

### PRIORITY 4 — Proofread for AI-writing markers
Remove all: "delve into", "it is important to note", "furthermore", "comprehensive",
"multifaceted", "nuanced", "in conclusion". Vary sentence length. Passive voice for methods,
active voice for contributions.

---

## File Structure
```
scripts/
  01_collect_github_profiles.py   — GitHub data collection (ran, produced 46 profiles)
  02_meq_survey.py                — Full 19-item MEQ (not used)
  02b_rmeq_survey.py              — 5-item rMEQ (circulated, ~10-12 responses)
  03_analyse_and_plot.py          — All algorithmic analyses + figures (DONE)
  04_stackoverflow_crossval.py    — SO cross-validation (SO users inactive, used synthetic)
  data/
    profiles_summary.csv          — 46 qualified developer profiles
    hours/{username}_hours.json   — commit hour lists per developer
    checkpoint.json               — 150 processed, 46 qualified
  results/                        — ALL PAPER FIGURES AND TABLES (READY)
    paper_stats_master.json       — master numbers file
    fig2_crossval_and_distribution.pdf/.png
    fig3_compatibility_model.pdf/.png
    fig4_cat_early_stop.pdf/.png
    fig5_monte_carlo_convergence.pdf/.png
    fig_dimensions_weights.pdf/.png
    table1_chronotype_per_user.csv
    table2_chronotype_distribution.csv
docs/
  RESEARCH_PAPER_PLAN.md          — Full paper plan with section-by-section guide
apps/backend/
  app/github_client.py            — chronotype algorithm (source of truth)
  app/services.py                 — CAT, Monte Carlo, compatibility (source of truth)
  app/schemas.py                  — ASHTAKOOT_DIMENSIONS, ASHTAKOOT_WEIGHTS
```

---

## Key Instruction for Next Session

**The main task is: write the full 6-page IEEE paper as a .tex file (IEEEtran format) or as a detailed section-by-section Word document.**

Start by reading:
1. `docs/RESEARCH_PAPER_PLAN.md` — complete writing guide
2. `scripts/results/paper_stats_master.json` — all numbers
3. `apps/backend/app/github_client.py` — chronotype algorithm
4. `apps/backend/app/services.py` (lines 558–772) — compatibility, CAT, Monte Carlo

Then write Section I (Introduction) first. Use the exact numbers above. Do not invent any results.

The author name for the paper is the GitHub handle **1mystic**. Affiliation: IIT Madras (email: 23f2004201@ds.study.iitm.ac.in).
