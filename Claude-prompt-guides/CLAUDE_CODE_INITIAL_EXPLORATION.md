# GitSyntropy: Initial Project Exploration Guide
## Step-by-Step Instructions to Get Started with Claude Code

Follow this guide **exactly once** at the very beginning to get Claude Code oriented to your GitSyntropy project.

---

## STEP 1: Copy the Master Prompt

Go to your VS Code with Claude Code extension open.

**Click in the prompt box and paste this entire prompt:**

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
1. Explore the project root directory
2. After reading the codebase, report back with status
3. I'll guide you through building features one at a time

Please start by telling me the path to your project root directory. 
I will then explore the scaffolding and give you a comprehensive assessment.

Ready? Provide the project path (or use @project-root if in the project already).
```

**Click "Send" in Claude Code.**

---

## STEP 2: Provide Project Path

Claude will ask you for the project path. You can either:

**Option A: Use the @-mention shortcut**
In your prompt, type:
```
@project-root
```
(This assumes you've opened the project folder in VS Code and are in the correct directory)

**Option B: Provide the full path**
```
/path/to/gitsyntropy
```

**Send this and wait for Claude to explore.**

---

## STEP 3: Claude Reads the Project

Claude Code will:
1. List the directory structure
2. Read key files (requirements.txt, package.json, main.py, etc.)
3. Understand what's already built
4. Identify what's missing

**This may take 30 seconds to 1 minute.** Let it finish.

---

## STEP 4: Review Claude's Assessment

Claude will report something like:

```
✓ ASSESSMENT COMPLETE

Overall Completion: 25%

BACKEND STATUS:
✓ FastAPI app initialized
◐ Database models partially defined
✗ GitHub Analyst Agent (skeleton only)
✗ Psychometric Agent (missing)
...

FRONTEND STATUS:
✓ Astro project set up
◐ Authentication pages started
✗ Dashboard components missing
...

CRITICAL GAPS:
- No Supabase schema yet (blocks all agents)
- No LangGraph orchestrator (blocks feature 5+)

RECOMMENDED BUILD ORDER:
1. Supabase schema setup
2. Feature 1: GitHub OAuth (needs users table)
3. Feature 2: GitHub Analyst Agent
...

Ask me to start with [Feature 1] when ready.
```

**Read this carefully.** If Claude's assessment is accurate, reply:**

```
This assessment looks right. Let's build Feature 1: GitHub OAuth & User Authentication.
```

**If something is wrong, correct Claude:**

```
Actually, [detail] is already done. We're further along.
Also, [new detail] that I need you to know.

Given that, build order should be: [new order]
```

---

## STEP 5: Start Building Feature 1

Claude will ask for confirmation. Reply with the relevant feature prompt from `CLAUDE_CODE_PROMPT_STRATEGY.md` **Section 4**.

For example:

```
BUILD FEATURE: GitHub OAuth & User Authentication

CONTEXT:
Users must authenticate via GitHub OAuth to access the app. This is the foundation for all other features.

[... rest of the prompt from the strategy document ...]
```

**Paste the entire feature prompt.** Claude will then:
1. Understand the requirements
2. Write the code
3. Create tests
4. Report what's done

---

## STEP 6: Review & Iterate

When Claude reports a feature is complete:

1. **Read the code** (ask Claude to show you key files)
2. **Review tests** (ask Claude to run them)
3. **Ask questions** if anything is unclear
4. **Request changes** if needed

When satisfied:

```
Great! Feature 1 is complete. Let's move to Feature 2: GitHub Analyst Agent.
```

**Then paste Feature 2 prompt from the strategy document.**

---

## DURING DEVELOPMENT: How to Use Claude Code

### If you're stuck:
```
I'm seeing this error: [error message]

Can you help debug? The endpoint is [/path] and the error happens when [condition].
```

### If you need clarification:
```
For Feature [X], requirement [Y] is unclear. Should we [option A] or [option B]?
```

### If you want to understand code:
```
@path/to/file.py

Explain this file in 3 sentences. What are the important functions?
```

### If you want to optimize:
```
@path/to/file.py

This code works but might be slow. Can you optimize it? Specifically:
- [concern 1]
- [concern 2]

Then show me before/after timing.
```

---

## DAILY WORKFLOW

Each time you return to the project, start with:

```
@project-root

I'm back. Give me a quick status:
1. **Overall completion**: [X]%
2. **What was done last session**: [summary]
3. **Currently broken**: Any failing tests?
4. **Next task**: What should we build?

Keep it to 5 bullet points.
```

Then continue from where you left off.

---

## CHECKPOINTS: Save Progress

After each feature is complete, take a checkpoint:

1. **Commit your code to git**:
   ```bash
   git add .
   git commit -m "feat: Feature X complete - [description]"
   git push
   ```

2. **Update the progress checklist** in `CLAUDE_CODE_PROMPT_STRATEGY.md` Section 5

3. **Note any gotchas** (things that were harder than expected) — helpful for later features

---

## TROUBLESHOOTING

### Claude can't find the project files
→ Make sure you're in the project root directory in VS Code  
→ Type `@project-root` or use the full path `/path/to/gitsyntropy`

### Claude generated code that doesn't compile/run
→ Ask Claude to fix it: "This code has an error at line X: [error]. Fix it."  
→ Or ask for help: "Can you test this locally? Here's the error I get: [error]"

### Tests are failing
→ Ask Claude: "Test [test_name] is failing. Why? Fix it."  
→ Claude will debug and fix the test or the code

### I changed something and now it's broken
→ Rollback: `git revert HEAD`  
→ Then ask Claude: "I reverted the last change. Now rebuild Feature X properly."

### I don't understand how two components connect
→ Ask Claude: "How does @module_A.py interact with @module_B.py?"  
→ Claude will explain the flow

---

## WORKING WITH DIFFERENT FILES

### Python Backend Code
```
@app/agents/github_analyst.py

Explain this agent. What does it do? How does it integrate with other agents?
```

### Frontend Components
```
@src/components/AshtakootRadar.tsx

Is this component fully functional? Show me an example of how to use it.
```

### Database Schema
```
@supabase/migrations/001_initial.sql

What tables exist? How are they related? Show me as a diagram.
```

### Tests
```
@tests/test_compatibility_engine.py

Run these tests. Show me the coverage report.
```

---

## ESTIMATED TIMELINE

If you use Claude Code efficiently:

- **Feature 1** (GitHub OAuth): 30-45 min
- **Feature 2** (GitHub Analyst): 45-60 min
- **Feature 3** (Psychometric): 45-60 min
- **Feature 4** (Compatibility Engine): 60 min
- **Feature 5** (LangGraph Orchestration): 60 min
- **Feature 6** (Claude Synthesis): 45 min
- **Feature 7** (Frontend Dashboard): 60-90 min
- **Feature 8** (Team Management): 60 min
- **Feature 9** (Error Handling, Performance): 45 min
- **Feature 10** (Testing, Docs, Deployment): 60 min

**Total: 8-10 hours of focused work** to go from scaffolding to deployment-ready.

---

## NEXT STEPS

1. **Read this guide fully**
2. **Open your GitSyntropy project in VS Code** with Claude Code extension
3. **Copy the Master Prompt** from Section 1 (or Section 1 of CLAUDE_CODE_PROMPT_STRATEGY.md)
4. **Paste it in Claude Code's prompt box**
5. **Type: `@project-root`**
6. **Send and wait for Claude's assessment**
7. **Review the assessment**
8. **Start building Feature 1**

You're ready! Let's build something great. 🚀

---

## SUPPORT

If you get stuck or need help:

1. **Check the Quick Reference**: `CLAUDE_CODE_QUICK_REFERENCE.md` has prompts for common tasks
2. **Refer to the detailed strategy**: `CLAUDE_CODE_PROMPT_STRATEGY.md` has full feature requirements
3. **Ask Claude**: Claude is very good at answering questions if you explain the context

Good luck! 🎯
