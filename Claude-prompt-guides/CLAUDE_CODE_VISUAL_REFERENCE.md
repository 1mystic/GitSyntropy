# GitSyntropy: Claude Code - Visual Reference & Summary

This document provides a quick visual overview of the entire Claude Code strategy.

---

## THE COMPLETE WORKFLOW

```
┌─────────────────────────────────────────────────────────────────────┐
│                    YOU OPEN VS CODE                                 │
│                 (Claude Code Extension Ready)                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: COPY MASTER PROMPT                                          │
│ (From CLAUDE_CODE_INITIAL_EXPLORATION.md)                           │
│ Gives Claude the entire project vision, stack, agents               │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: PROVIDE PROJECT PATH                                        │
│ Type: @project-root (or full path)                                  │
│ Claude explores the entire codebase                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: CLAUDE ASSESSES STATUS                                      │
│ "You're at 25% complete. Here's what exists, what's missing,       │
│  and what I recommend building next."                               │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: YOU CONFIRM & PICK A FEATURE                                │
│ Copy Feature [X] prompt from CLAUDE_CODE_PROMPT_STRATEGY.md         │
│ "Build Feature 1: GitHub OAuth & User Authentication"              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
           ┌─────────────────┴─────────────────┐
           │                                   │
           ▼                                   ▼
    ┌──────────────────┐            ┌──────────────────┐
    │   CLAUDE BUILDS  │            │    REVIEWS CODE  │
    │                  │            │                  │
    │ • Reads existing │ ──────┬──► │ • Understands    │
    │   code structure │        │    │   what was built │
    │ • Writes new     │        │    │ • Asks questions │
    │   feature code   │        │    │ • Requests fixes │
    │ • Creates tests  │        │    │ • Approves       │
    │ • Runs tests     │        │    │                  │
    │ • Reports done   │        │    │ ✓ FEATURE READY  │
    └──────────────────┘        │    └──────────────────┘
                                │
                                ▼
                      ┌──────────────────┐
                      │ NEXT FEATURE     │
                      │                  │
                      │ Copy Feature [X] │
                      │ prompt, send it, │
                      │ Claude builds    │
                      │                  │
                      └──────────────────┘
                              │
                 ┌────────────┴────────────┐
                 │                        │
              REPEAT                   ...until
              FOR ALL                all 10 features
              10 FEATURES            are complete
                 │                        │
                 └────────────┬───────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  PRE-DEPLOY      │
                    │  CHECKLIST       │
                    │  (All tests pass,│
                    │   code ready)    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ DEPLOY TO        │
                    │ Railway (backend)│
                    │ Vercel (frontend)│
                    └──────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  LIVE! 🚀        │
                    │ GitSyntropy      │
                    │ Production Ready │
                    └──────────────────┘
```

---

## THE 10 FEATURES AT A GLANCE

| # | Feature | Backend | Frontend | Dependencies | Est. Time |
|---|---------|---------|----------|--------------|-----------|
| 1 | GitHub OAuth | auth.py, JWT | login page, callback | Supabase users table | 30-45min |
| 2 | GitHub Analyst | GraphQL client, K-Means | status page | users table from #1 | 45-60min |
| 3 | Psychometric | 8-question quiz, CAT | assessment form | GitHub profiles from #2 | 45-60min |
| 4 | Compatibility Engine | scoring algorithms, Monte Carlo | - (backend only) | psychometric scores from #3 | 60min |
| 5 | LangGraph Orchestration | state machine, agent DAG, WebSocket | - (backend focus) | all agents from #1-4 | 60min |
| 6 | Claude Synthesis | Claude API client, streaming | - (backend focus) | orchestration from #5 | 45min |
| 7 | Frontend Dashboard | - (frontend focus) | radar, heatmap, timeline charts | orchestration from #5 | 60-90min |
| 8 | Team Management | team CRUD, invite system, simulator | forms, dialogs, modals | all previous features | 60min |
| 9 | Error Handling & Performance | rate limiting, timeouts, logging | error boundaries, retry logic | all features | 45min |
| 10 | Testing & Deployment | pytest, coverage, Railway config | Vercel config, docs | all features | 60min |

**Total: ~8-10 hours of focused development**

---

## WHICH FILE TO USE WHEN

### Starting Out
Use: **CLAUDE_CODE_INITIAL_EXPLORATION.md**
- Master Prompt (the most important thing)
- Step-by-step walkthrough
- What to do first

### Daily Development
Use: **CLAUDE_CODE_QUICK_REFERENCE.md**
- Copy-paste prompts for common tasks
- Debugging, testing, documentation
- Fast answers to quick questions

### Building a Feature
Use: **CLAUDE_CODE_PROMPT_STRATEGY.md**
- Section 1: Master Prompt (for first time)
- Section 4: Feature-by-feature prompts
- Section 5: Progress checklist
- Section 6: How to communicate with Claude

### When Stuck
Use: **CLAUDE_CODE_QUICK_REFERENCE.md**
- Debugging section
- LangGraph debugging
- Reset & rollback prompts

---

## THE 3-TIER PROMPTING STRATEGY

### Tier 1: Master Context (Use Once at Start)
```
"You are building GitSyntropy, an AI-native team composition 
intelligence platform. Here's the vision, stack, and architecture..."

✓ Claude understands the whole project
✓ Claude knows all 4 agents, the 8 dimensions, the scoring algorithm
✓ Claude knows what the end result looks like
```

### Tier 2: Feature Prompts (Use for Each Feature)
```
"BUILD FEATURE: [Feature Name]

CONTEXT: [Why this feature matters]
REQUIREMENTS: [Exactly what to build]
DELIVERABLES: [Code, tests, docs]
CONSTRAINTS: [Quality standards]"

✓ Claude builds one feature completely
✓ Claude includes tests
✓ Claude integrates with existing code
```

### Tier 3: Quick Reference (Use During Development)
```
"Why is this test failing?"
"How does X connect to Y?"
"Can you optimize this for performance?"
"Debug this API error: [error message]"

✓ Quick answers to specific questions
✓ Debugging, optimization, clarification
✓ No need to re-explain the whole project
```

---

## WHEN TO USE WHAT

### You're starting from scratch
→ Use: CLAUDE_CODE_INITIAL_EXPLORATION.md (Step 1-3)

### Claude is building a feature
→ Let Claude work, answer clarifying questions

### You want to debug a failure
→ Use: CLAUDE_CODE_QUICK_REFERENCE.md (Debugging section)

### You want to add logging or optimize
→ Use: CLAUDE_CODE_QUICK_REFERENCE.md (Quick Wins section)

### You're ready for the next feature
→ Use: CLAUDE_CODE_PROMPT_STRATEGY.md (Section 4)

### You're confused about how code works
→ Use: CLAUDE_CODE_QUICK_REFERENCE.md (Understanding Code section)

### It's been a while since you worked on it
→ Start with: "Where are we at?" prompt (Quick Reference)

### You need to deploy
→ Use: CLAUDE_CODE_PROMPT_STRATEGY.md (Section 7: Deployment)

---

## QUICK COMMAND REFERENCE

### Things Claude Can Do Immediately

| Need | Prompt | Where |
|------|--------|-------|
| Build a full feature | "BUILD FEATURE: [Name]" | Prompt Strategy Sec 4 |
| Run all tests | "Run: pytest --cov" | Quick Reference |
| Debug an error | "Test X is failing: [error]" | Quick Reference |
| Understand code | "@file.py Explain this file" | Quick Reference |
| Optimize performance | "@file.py Optimize this" | Quick Reference |
| Add tests for function | "@file.py#lines Test this function" | Quick Reference |
| Check status | "Where are we at?" | Quick Reference |
| Deploy to production | "Deploy to Railway" | Prompt Strategy Sec 7 |

---

## SUCCESS CRITERIA

### For Each Feature
- ✓ Code is written and complete (no TODOs)
- ✓ Tests pass (pytest --cov shows good coverage)
- ✓ No console errors or warnings
- ✓ Integrates with existing features
- ✓ Documented (docstrings, README updated)

### For the Whole Project
- ✓ All 10 features complete
- ✓ All tests pass (> 80% coverage)
- ✓ Both backend and frontend deploy successfully
- ✓ End-to-end workflow works (login → analyze team → see results)
- ✓ Zero TODOs in code
- ✓ Production-ready error handling
- ✓ Performance targets met (< 10s for team analysis)

---

## ESTIMATED MILESTONES

| Week | Features | Status |
|------|----------|--------|
| Week 1 | 1-2 (Auth, GitHub) | Backend foundation |
| Week 2 | 3-4 (Psychometric, Compatibility) | Core algorithms |
| Week 3 | 5-6 (Orchestration, Synthesis) | Agentic system |
| Week 4 | 7-8 (Dashboard, Team Mgmt) | Frontend complete |
| Week 5 | 9-10 (Polish, Deploy) | Production ready |

**Total: 5 weeks of part-time work (or 2-3 weeks of full-time)**

---

## KEY FILES IN YOUR WORKFLOW

```
project-root/
├── CLAUDE_CODE_INITIAL_EXPLORATION.md    ← START HERE (first time only)
├── CLAUDE_CODE_PROMPT_STRATEGY.md        ← Feature templates & full reference
├── CLAUDE_CODE_QUICK_REFERENCE.md        ← Daily prompts & quick answers
├── 01_GitSyntropy_Architecture.md        ← The vision & full spec
│
├── app/                                   ← Backend code (Claude builds this)
│   ├── agents/
│   │   ├── github_analyst.py
│   │   ├── psychometric_agent.py
│   │   ├── compatibility_engine.py
│   │   └── synthesis_agent.py
│   ├── orchestration/
│   │   ├── state.py
│   │   └── graph.py
│   ├── routes/
│   ├── models/
│   ├── clients/
│   └── main.py
│
├── src/                                   ← Frontend code (Claude builds this)
│   ├── pages/
│   │   ├── login.astro
│   │   ├── dashboard.astro
│   │   └── teams/
│   ├── components/
│   │   ├── AshtakootRadar.tsx
│   │   ├── ChronotypeHeatmap.tsx
│   │   ├── AgentStreamView.tsx
│   │   └── ...
│   └── utils/
│
├── tests/                                 ← Tests (Claude writes these)
│   ├── test_auth.py
│   ├── test_github_analyst.py
│   └── ...
│
├── supabase/                              ← Database (Claude creates migrations)
│   └── migrations/
│       ├── 001_create_users_table.sql
│       └── ...
│
└── .github/workflows/                     ← CI/CD (Claude configures)
    ├── ci.yml
    └── deploy.yml
```

---

## TALKING TO CLAUDE CODE

### Good Prompts (Clear, Specific)
```
"The test_chronotype_detection test is failing because the K-Means 
output doesn't match the expected cluster. Can you debug and fix it?"

"Build Feature 4: Compatibility Engine. Requirements: [paste from document]"

"@app/agents/github_analyst.py - Explain this file and how it connects 
to the orchestrator."
```

### Bad Prompts (Vague, Unclear)
```
"Make it work"
"Fix the thing"
"Why isn't this working?" (without error message)
"Build the feature" (which feature?)
```

### Medium Prompts (Could be Better)
```
"Add error handling" (add it WHERE? for WHAT errors?)
"Make it faster" (WHAT'S SLOW? Show me a profile)
"Write tests" (for WHICH function? What scenarios?)
```

### Best Practice
**Always include:**
1. What you want Claude to do
2. Why it matters (context)
3. Where the relevant code is (@-mention files)
4. If an error, the full error message
5. What success looks like

---

## COMMON PATTERNS

### Pattern 1: Build and Test
```
Claude: "I've built Feature 1: GitHub OAuth"
You: "Show me the code" (Claude pastes it)
You: "Run pytest tests/test_auth.py -v" (Claude runs it)
You: "Show coverage report"
You: "✓ Looks good, let's move to Feature 2"
```

### Pattern 2: Fix a Bug
```
You: "Test test_nadi_scoring is failing: [error message]"
Claude: "I see the issue. [explanation]. Fixing..."
Claude: "Fixed. Re-running tests..."
Claude: "All tests pass now."
You: "✓ Thanks!"
```

### Pattern 3: Understand Code
```
You: "@app/orchestration/graph.py - How does the DAG work?"
Claude: "The graph has 4 nodes (GitHub → Psychometric → Compatibility → Synthesis).
Each node updates the state. Here's the flow: [explanation]"
You: "Got it. Now build Feature 5."
```

---

## POWER MOVES

### Move 1: Batch Build
```
"I have 2 hours. Can you build Features 2 and 3 today?
- Feature 2 must complete first (required by 3)
- Feature 3 depends on #2
Build 2 fully with tests, then 3, then integrate.
Go!"
```

### Move 2: Pair Program
```
"Let's pair on Feature 5: LangGraph Orchestration.
First, show me the plan. Then we'll code together.
I'll review each piece before you move on."
```

### Move 3: Full Rollback
```
"Things got messy. Rollback to commit [hash].
Then rebuild Feature [X] properly from the working state."
```

---

## WHEN EVERYTHING IS DONE

```
[ ] All 10 features complete
[ ] All tests passing (> 80% coverage)
[ ] No TODOs in code
[ ] README complete with architecture
[ ] Deployed to Railway (backend) + Vercel (frontend)
[ ] Demo video recorded
[ ] GitHub repo has clean commit history

NEXT: Share on HackerNews, ProductHunt, LinkedIn with the story:
"I built a multi-agent AI system that analyzes team dynamics 
using the Vedic Ashtakoot compatibility framework..."
```

---

## FINAL NOTES

- **This strategy is battle-tested**: It's designed for maximum efficiency with Claude Code
- **Be specific with prompts**: The more detail, the better Claude performs
- **Trust the process**: Follow the 10-feature roadmap in order
- **Ask questions early**: If a requirement is unclear, ask Claude before building
- **Save time by batching**: Build multiple features in one session if you have time
- **Keep this document open**: Refer to it constantly while developing

---

## YOU'RE READY 🚀

1. Open VS Code with Claude Code extension
2. Use `CLAUDE_CODE_INITIAL_EXPLORATION.md` to start
3. Follow the 10-feature roadmap
4. Refer to `CLAUDE_CODE_QUICK_REFERENCE.md` daily
5. Use `CLAUDE_CODE_PROMPT_STRATEGY.md` for each feature

**Estimated time: 8-10 hours to go from scaffolding to production-ready.**

Let's build GitSyntropy! 🎯
