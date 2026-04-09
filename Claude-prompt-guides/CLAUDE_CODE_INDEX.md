# GitSyntropy: Claude Code Complete Prompt Index
## Master Navigation Document

Welcome! This index helps you find exactly what you need at every stage of building GitSyntropy with Claude Code.

---

## 📋 QUICK START (Read First)

### For First-Time Setup
1. Read: **CLAUDE_CODE_INITIAL_EXPLORATION.md** (Step 1-4)
2. Copy the Master Prompt into Claude Code
3. Let Claude explore your project
4. Review Claude's assessment
5. Start building Feature 1

**Expected time: 10 minutes to get oriented**

### For Daily Development
1. Open **CLAUDE_CODE_QUICK_REFERENCE.md**
2. Find the prompt that matches what you need
3. Copy-paste it into Claude Code
4. Iterate based on Claude's response

**Expected time: 30-60 minutes per feature**

---

## 📚 THE FOUR MAIN DOCUMENTS

### 1. **CLAUDE_CODE_INITIAL_EXPLORATION.md**
**Purpose:** Getting started — one-time setup
**Contains:**
- Step-by-step walkthrough (Steps 1-6)
- Master Prompt (the vision & architecture)
- How to provide project path
- How to review Claude's assessment
- Daily workflow instructions
- Troubleshooting section

**Use when:**
- ✓ Starting the project for the first time
- ✓ You've been away and need to get re-oriented
- ✓ Something broke and you need to reset
- ✓ New person joining the project

**Skip this if:** You've already done the initial exploration and Claude has assessed your project

---

### 2. **CLAUDE_CODE_PROMPT_STRATEGY.md**
**Purpose:** Complete reference — the blueprint for all features
**Contains:**
- Section 1: Master Prompt (for reference)
- Section 2: Project Assessment Prompt
- Section 3: Feature-by-feature build prompts
- Section 4: All 10 Feature prompts (copy-paste ready)
  - Feature 1: GitHub OAuth & Auth
  - Feature 2: GitHub Analyst Agent
  - Feature 3: Psychometric Agent
  - Feature 4: Compatibility Engine
  - Feature 5: LangGraph Orchestration
  - Feature 6: Claude Synthesis
  - Feature 7: Frontend Dashboard
  - Feature 8: Team Management
  - Feature 9: Error Handling & Performance
  - Feature 10: Testing & Deployment
- Section 5: Progress Checklist
- Section 6: Communication Protocol
- Section 7: Deployment Checklist

**Use when:**
- ✓ Building a specific feature
- ✓ You need the exact requirements
- ✓ You want to understand what needs to be done
- ✓ Pre-deployment (final checklist)

**Skip this if:** You just need a quick answer to a simple question

---

### 3. **CLAUDE_CODE_QUICK_REFERENCE.md**
**Purpose:** Daily prompts — copy-paste for common tasks
**Contains:**
- Getting Oriented prompts
- Understanding Code prompts
- Writing Code prompts
- Debugging prompts
- Database prompts
- Frontend prompts
- Testing prompts
- Deployment prompts
- Advanced prompts

**Use when:**
- ✓ Debugging a failing test
- ✓ Explaining code to you
- ✓ Optimizing performance
- ✓ Adding a new component
- ✓ Any daily development question
- ✓ You need a quick, specific answer

**Skip this if:** You're building a whole new feature (use Feature prompts instead)

---

### 4. **CLAUDE_CODE_VISUAL_REFERENCE.md**
**Purpose:** Visual overview — see the big picture at a glance
**Contains:**
- Workflow diagram
- All 10 features summary table
- File location guide
- 3-tier prompting strategy
- When to use what table
- Command reference
- Success criteria
- Milestones & timeline
- Common patterns
- Power moves

**Use when:**
- ✓ You want the overview (what takes how long?)
- ✓ You need to understand the complete workflow
- ✓ You want to see milestones & timeline
- ✓ You're planning your week
- ✓ You're explaining the project to someone

**Skip this if:** You're in the middle of coding and need a specific answer

---

## 🎯 FINDING WHAT YOU NEED

### "I'm starting a new project with Claude Code"
→ Read: **CLAUDE_CODE_INITIAL_EXPLORATION.md** (full document)

### "I need to build Feature [X]"
→ Go to: **CLAUDE_CODE_PROMPT_STRATEGY.md** Section 4 → Find Feature [X] → Copy-paste prompt

### "Test [name] is failing, help debug"
→ Go to: **CLAUDE_CODE_QUICK_REFERENCE.md** → Debugging section → "Why is this test failing?"

### "I want to understand how [code] works"
→ Go to: **CLAUDE_CODE_QUICK_REFERENCE.md** → Understanding Code section → "Explain this module"

### "How long will Feature [X] take?"
→ Go to: **CLAUDE_CODE_VISUAL_REFERENCE.md** → Features table → Find Feature [X]

### "What's the overall workflow?"
→ Read: **CLAUDE_CODE_VISUAL_REFERENCE.md** (the workflow diagram at top)

### "I'm stuck and don't know where to start"
→ Go to: **CLAUDE_CODE_QUICK_REFERENCE.md** → "Where are we at?" prompt

### "I need to deploy to production"
→ Go to: **CLAUDE_CODE_PROMPT_STRATEGY.md** → Section 7: Deployment Checklist

---

## 🔄 TYPICAL DEVELOPMENT CYCLE

### Monday Morning (Fresh Start)
1. Open VS Code, Claude Code extension
2. Use: **CLAUDE_CODE_QUICK_REFERENCE.md** → "Where are we at?" prompt
3. Read Claude's status report
4. Decide what feature to build today

### Building a Feature (2 hours)
1. Get the Feature prompt from: **CLAUDE_CODE_PROMPT_STRATEGY.md** Section 4
2. Copy-paste into Claude Code
3. Claude builds → asks questions → you answer
4. Claude reports feature complete
5. You review code (ask clarifying questions)
6. Mark feature complete in checklist

### Daily Debugging (30 min)
1. Test or endpoint breaks
2. Use: **CLAUDE_CODE_QUICK_REFERENCE.md** → "Why is this test failing?"
3. Claude debugs and fixes
4. Tests pass
5. Continue

### Wednesday Evening (Optimization)
1. Code works but might be slow
2. Use: **CLAUDE_CODE_QUICK_REFERENCE.md** → "Refactor for performance"
3. Claude optimizes
4. Verify tests still pass

### Friday Afternoon (Status Check)
1. Use: **CLAUDE_CODE_VISUAL_REFERENCE.md** → Progress table
2. Check off completed features
3. Plan next week's work

### Friday Evening (Commit & Backup)
1. `git commit -m "feat: Features X, Y, Z complete"`
2. `git push`
3. Update checklist in **CLAUDE_CODE_PROMPT_STRATEGY.md** Section 5

---

## 📍 THE FEATURE-BY-FEATURE PATH

Follow this exact sequence. Each feature depends on the previous one.

```
FEATURE 1: GitHub OAuth & User Authentication
├─ Files: app/auth.py, routes/auth.py, pages/login.astro
├─ Uses: Supabase users table
├─ Tests: test_auth.py
└─ Prompt location: CLAUDE_CODE_PROMPT_STRATEGY.md Section 4
    
    ↓

FEATURE 2: GitHub Analyst Agent
├─ Files: app/agents/github_analyst.py, routes/github.py
├─ Uses: users table from #1, github_profiles table
├─ Tests: test_github_analyst.py
└─ Prompt location: CLAUDE_CODE_PROMPT_STRATEGY.md Section 4

    ↓

FEATURE 3: Psychometric Agent & Assessment
├─ Files: app/agents/psychometric_agent.py, pages/assessment.astro
├─ Uses: psychometric_assessments table
├─ Tests: test_psychometric.py
└─ Prompt location: CLAUDE_CODE_PROMPT_STRATEGY.md Section 4

    ↓

FEATURE 4: Compatibility Engine
├─ Files: app/agents/compatibility_engine.py, routes/compatibility.py
├─ Uses: team_scores, team_members tables
├─ Tests: test_compatibility_engine.py
└─ Prompt location: CLAUDE_CODE_PROMPT_STRATEGY.md Section 4

    ↓

FEATURE 5: LangGraph Orchestration & WebSocket
├─ Files: app/orchestration/state.py, graph.py, websocket_manager.py
├─ Uses: agent_runs, agent_events tables
├─ Tests: test_orchestration.py
└─ Prompt location: CLAUDE_CODE_PROMPT_STRATEGY.md Section 4

    ↓

FEATURE 6: Claude Synthesis Agent
├─ Files: app/agents/synthesis_agent.py
├─ Uses: Claude API (streaming)
├─ Tests: test_synthesis_agent.py
└─ Prompt location: CLAUDE_CODE_PROMPT_STRATEGY.md Section 4

    ↓

FEATURE 7: Frontend Dashboard
├─ Files: pages/dashboard.astro, components/AshtakootRadar.tsx, etc.
├─ Uses: All orchestration infrastructure from #5
├─ Tests: Component tests
└─ Prompt location: CLAUDE_CODE_PROMPT_STRATEGY.md Section 4

    ↓

FEATURE 8: Team Management UX
├─ Files: pages/teams/new.astro, components/InviteDialog.tsx, etc.
├─ Uses: teams, team_invites tables
├─ Tests: test_team_management.py
└─ Prompt location: CLAUDE_CODE_PROMPT_STRATEGY.md Section 4

    ↓

FEATURE 9: Error Handling & Performance
├─ Files: middleware/error_handler.py, rate_limit.py, etc.
├─ Uses: All existing features
├─ Tests: test_error_handling.py
└─ Prompt location: CLAUDE_CODE_PROMPT_STRATEGY.md Section 4

    ↓

FEATURE 10: Testing, Documentation & Deployment
├─ Files: pytest.ini, README.md, railway.toml, vercel.json
├─ Uses: All code from #1-9
├─ Tests: All features
└─ Prompt location: CLAUDE_CODE_PROMPT_STRATEGY.md Section 4

    ↓

🚀 DEPLOYMENT READY!
   - Run: CLAUDE_CODE_PROMPT_STRATEGY.md Section 7
   - Deploy to Railway + Vercel
   - Launch on HackerNews/ProductHunt
```

---

## 💡 EXAMPLE WORKFLOWS

### Workflow 1: Building Feature 2

```
Time: Monday 9 AM
Task: Build GitHub Analyst Agent (Feature 2)

Step 1: Open CLAUDE_CODE_PROMPT_STRATEGY.md
Step 2: Navigate to Section 4
Step 3: Find "FEATURE 2: GitHub Analyst Agent"
Step 4: Copy the entire prompt
Step 5: Open Claude Code in VS Code
Step 6: Paste the prompt in the prompt box
Step 7: Wait for Claude to explore existing code
Step 8: Claude asks: "Should I assume PyGithub is already in requirements.txt?"
Step 9: You answer: "Yes, also add gql if needed"
Step 10: Claude builds the feature
Step 11: Claude reports: "Feature 2 complete. Test coverage 95%"
Step 12: You review the code, ask questions
Step 13: You mark Feature 2 as ✓ in the checklist
Step 14: Commit: git commit -m "feat: Feature 2 - GitHub Analyst Agent"
Step 15: Start Feature 3

Time elapsed: ~50 minutes
```

### Workflow 2: Debugging a Test

```
Time: Tuesday 2 PM
Task: Fix failing test

Step 1: You run: pytest tests/test_compatibility_engine.py
Step 2: Test fails: "AssertionError: expected 28.5, got 22.3"
Step 3: Open CLAUDE_CODE_QUICK_REFERENCE.md
Step 4: Go to Debugging section
Step 5: Use prompt: "Why is this test failing?"
Step 6: Copy the prompt, customize it with the actual error
Step 7: Paste in Claude Code
Step 8: Claude analyzes the test
Step 9: Claude finds the bug: "The variance weighting is inverted"
Step 10: Claude fixes the code
Step 11: Claude runs tests: "All tests pass now"
Step 12: Commit: git commit -m "fix: Variance weighting in compatibility scoring"

Time elapsed: ~15 minutes
```

### Workflow 3: Building Multiple Features in One Day

```
Time: Saturday, Full Day

Morning Session (Features 1-2):
- Start with Feature 1 prompt (GitHub OAuth)
- Claude builds, you review: 45 min
- Feature 1 done ✓
- Start with Feature 2 prompt (GitHub Analyst)
- Claude builds, you review: 55 min
- Feature 2 done ✓
- Commit & push

Afternoon Session (Features 3-4):
- Start with Feature 3 prompt (Psychometric)
- Claude builds, you review: 50 min
- Feature 3 done ✓
- Start with Feature 4 prompt (Compatibility)
- Claude builds, you review: 60 min
- Feature 4 done ✓
- Commit & push

Evening Session (Status & Testing):
- All tests pass: pytest --cov shows 85%+ coverage
- Commit all changes
- Update progress checklist
- Plan next session

Total features built: 4
Total time: ~5 hours
Completion: 40% of project
```

---

## 🛠️ TOOL OVERVIEW

### What Claude Code Can Do
- ✓ Read your entire codebase instantly
- ✓ Understand architecture and patterns
- ✓ Write production-ready code
- ✓ Run tests and show results
- ✓ Debug failing tests
- ✓ Optimize performance
- ✓ Create database migrations
- ✓ Generate documentation
- ✓ Deploy to production
- ✓ Answer architectural questions

### What You Do
- ✓ Provide context (project path, requirements)
- ✓ Ask questions (clear, specific prompts)
- ✓ Review code (make sure it's what you want)
- ✓ Make decisions (which feature next?)
- ✓ Commit to git (preserve history)
- ✓ Configure deployment (Railway, Vercel keys)

### The Partnership
```
You (Project Visionary)          Claude Code (Implementer)
─────────────────────────        ──────────────────────────
"Build Feature X"        ───→     Reads requirements
                         ←───     Asks clarifying questions
"Like this, not that"    ───→     Adjusts approach
                         ←───     Shows you the code
"Ship it"               ───→     Runs tests, reports done
                         ←───     "Feature complete ✓"
```

---

## 📊 PROGRESS TRACKING

### Use This Checklist
Location: **CLAUDE_CODE_PROMPT_STRATEGY.md** Section 5

Update it as features complete:
```
[✓] Feature 1: GitHub OAuth
[✓] Feature 2: GitHub Analyst
[ ] Feature 3: Psychometric
[ ] Feature 4: Compatibility
...

2/10 features complete (20%)
Estimated completion: [date]
```

### Track in Your Git Commits
```
feat: Feature 1 - GitHub OAuth & Auth
feat: Feature 2 - GitHub Analyst Agent
fix: Test failures in Feature 2
feat: Feature 3 - Psychometric Agent
...
```

---

## 🚀 THE FINAL DEPLOYMENT

When all 10 features are complete:

1. Check: **CLAUDE_CODE_PROMPT_STRATEGY.md** Section 7 (Pre-Deployment Checklist)
2. All tests pass
3. No TODOs in code
4. Deploy to Railway (FastAPI backend)
5. Deploy to Vercel (Astro frontend)
6. Verify live

Then:
- Share on HackerNews: "Show HN: GitSyntropy - Team analytics using Vedic framework + AI agents"
- ProductHunt launch
- LinkedIn post with the story
- Update portfolio with live link

---

## 📞 WHEN YOU GET STUCK

### Question Type 1: "How do I...?"
→ Use: **CLAUDE_CODE_QUICK_REFERENCE.md** (search the section)

### Question Type 2: "Why is this failing?"
→ Use: **CLAUDE_CODE_QUICK_REFERENCE.md** → Debugging section

### Question Type 3: "What should I build next?"
→ Use: **CLAUDE_CODE_VISUAL_REFERENCE.md** → Features table → Timeline

### Question Type 4: "I don't understand requirement X"
→ Use: **CLAUDE_CODE_PROMPT_STRATEGY.md** → Feature section → Read requirements

### Question Type 5: "How does X connect to Y?"
→ Use: **CLAUDE_CODE_QUICK_REFERENCE.md** → "How do A and B connect?"

### Question Type 6: "I'm completely lost"
→ Use: **CLAUDE_CODE_INITIAL_EXPLORATION.md** → "Where are we at?" prompt

---

## 📝 FILE LOCATIONS QUICK MAP

| Task | Document | Section |
|------|----------|---------|
| Get started | CLAUDE_CODE_INITIAL_EXPLORATION.md | Steps 1-4 |
| Build Feature 1 | CLAUDE_CODE_PROMPT_STRATEGY.md | Section 4 |
| Build Feature 2 | CLAUDE_CODE_PROMPT_STRATEGY.md | Section 4 |
| ... | ... | ... |
| Build Feature 10 | CLAUDE_CODE_PROMPT_STRATEGY.md | Section 4 |
| Debug a test | CLAUDE_CODE_QUICK_REFERENCE.md | Debugging |
| Understand code | CLAUDE_CODE_QUICK_REFERENCE.md | Understanding Code |
| Check progress | CLAUDE_CODE_PROMPT_STRATEGY.md | Section 5 |
| Deploy | CLAUDE_CODE_PROMPT_STRATEGY.md | Section 7 |
| Quick reference | CLAUDE_CODE_VISUAL_REFERENCE.md | Any section |

---

## 🎓 LEARNING RESOURCES

While building, you'll learn:
- **Multi-agent orchestration** (LangGraph, state management)
- **Async Python** (FastAPI, websockets)
- **React components** (TypeScript, hooks)
- **Database design** (Supabase, migrations)
- **API design** (REST, error handling)
- **Testing** (pytest, fixtures)
- **Deployment** (Railway, Vercel, CI/CD)
- **Team dynamics** (Ashtakoot algorithm, chronotype detection)

The codebase will become a portfolio project that explains:
- How you think about architecture
- How you write production code
- How you work with AI tools
- How you build complete systems

---

## ⏱️ TIME ESTIMATES

| Activity | Time |
|----------|------|
| Initial exploration (Steps 1-4) | 10 min |
| Feature 1 (GitHub OAuth) | 40 min |
| Feature 2 (GitHub Analyst) | 50 min |
| Feature 3 (Psychometric) | 50 min |
| Feature 4 (Compatibility) | 60 min |
| Feature 5 (LangGraph) | 60 min |
| Feature 6 (Synthesis) | 45 min |
| Feature 7 (Dashboard) | 75 min |
| Feature 8 (Team Management) | 60 min |
| Feature 9 (Error Handling) | 45 min |
| Feature 10 (Testing & Deployment) | 60 min |
| **TOTAL** | **~10 hours** |

---

## ✅ SUCCESS CHECKLIST

When you're done, you should have:
- [ ] All 10 features built and tested
- [ ] 80%+ code coverage
- [ ] Zero TODOs in code
- [ ] Backend deployed on Railway
- [ ] Frontend deployed on Vercel
- [ ] Both live and working
- [ ] Clean git history (20+ meaningful commits)
- [ ] Comprehensive README
- [ ] Demo video (4 min walkthrough)
- [ ] The story ready to tell in interviews

---

## 🎯 NEXT STEP

**Pick one:**

A) **First time building?**
   → Go to: **CLAUDE_CODE_INITIAL_EXPLORATION.md**

B) **Already explored and ready to build Feature X?**
   → Go to: **CLAUDE_CODE_PROMPT_STRATEGY.md** Section 4

C) **Something specific you need help with?**
   → Go to: **CLAUDE_CODE_QUICK_REFERENCE.md**

D) **Want to see the big picture first?**
   → Go to: **CLAUDE_CODE_VISUAL_REFERENCE.md**

---

## 📌 PIN THIS DOCUMENT

This index is your home base. Bookmark it or pin it.
- When lost, come back here
- It shows you exactly which document to use
- It explains the overall structure

You're ready to build! 🚀

Good luck with GitSyntropy! 🎯
