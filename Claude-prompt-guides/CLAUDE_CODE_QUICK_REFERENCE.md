# GitSyntropy: Claude Code Quick Reference
## Copy-Paste Prompts for Daily Development

Use these prompts directly in Claude Code to speed up common tasks. Customize the bracketed sections [like this].

---

## GETTING ORIENTED (Use at Start of Each Day)

### Prompt: "Where are we at?"

```
@project-root

Give me a quick status update:

1. **Overall completion**: [X]% done
2. **Last session**: What was completed?
3. **Currently broken**: Any failing tests or broken endpoints?
4. **Next immediate task**: What's the first thing we should tackle?
5. **Blockers**: Anything blocking progress?

Keep it to 5 bullet points. No long explanations.
```

---

## UNDERSTANDING CODE (Use When Confused About Existing Code)

### Prompt: "Explain this module"

```
@[file_path.py]

Explain this file in 3 sentences:
1. What does it do?
2. What functions/classes are important?
3. How does it connect to other parts of the system?

Then list any:
- Dependencies (external libraries)
- TODOs or incomplete sections
- Tests that exist for this code
```

### Prompt: "How do A and B connect?"

```
How does [module_A.py] interact with [module_B.py]?

Show:
1. What functions does A call from B?
2. What data is passed between them?
3. Where is this interaction tested?
4. Is there any shared state or database table involved?
```

---

## WRITING CODE (Use When Building a Feature)

### Prompt: "Complete the TODO"

```
@[file_path.py#start_line-end_line]

I see a TODO comment at line [X]: "[description]"

Complete this function/section. Requirements:
- [requirement 1]
- [requirement 2]
- [requirement 3]

Use existing patterns from this codebase. No external dependencies not already in requirements.txt.
```

### Prompt: "Add missing tests"

```
@tests/test_[module].py

The test file for [module.py] is missing tests for:
- [function/method 1]
- [function/method 2]
- [edge case 1]

Add comprehensive tests. Aim for 100% coverage of these functions.
Then run: pytest tests/test_[module].py -v
```

### Prompt: "Refactor for performance"

```
@[file_path.py]

This code works but might be slow. Profile it and optimize:

1. Identify the slowest functions (if you can estimate)
2. Suggest optimizations (caching, async/await, database queries)
3. Implement 2-3 quick wins
4. Show before/after timing (mock, if necessary)

Constraints:
- Don't change the function signature
- Don't add new dependencies
- All existing tests must still pass
```

---

## DEBUGGING (Use When Things Break)

### Prompt: "Why is this test failing?"

```
Test [test_name] in tests/test_[module].py is failing with:

[paste error message]

Debug by:
1. Show what the test is trying to do
2. What's the actual vs expected result?
3. Fix the code or the test (whichever is wrong)
4. Verify the fix works (re-run the test)
```

### Prompt: "API endpoint returns 500"

```
When I POST to /[endpoint], I get:
Status: 500
Error: [paste error message from logs]

Trace:
1. Is the error in the handler or a dependency?
2. What's the root cause?
3. Fix the code
4. Add better error handling/logging if it's a valid failure case
5. Show me what the endpoint should return on success (with example JSON)
```

### Prompt: "Integration is broken"

```
When the [Agent 1] finishes, it should pass data to [Agent 2], but:
- [what's happening instead]

Trace the issue:
1. Does Agent 1 produce the right output? (log if needed)
2. Is Agent 2 receiving it correctly? (add logs if needed)
3. Is the state passing correctly via LangGraph? (check state schema)
4. Fix the integration and verify with an end-to-end test
```

---

## DATABASE (Use When Schema Changes)

### Prompt: "Add a new table"

```
I need a new database table called "[table_name]" with these columns:
- [column 1]: [type] [constraints]
- [column 2]: [type] [constraints]
...

Also:
1. Create a SQLAlchemy model in app/models/[model_name].py
2. Create a migration file in supabase/migrations/
3. Update any agents that might read/write this table
4. Show me example queries for insert/select/update
```

### Prompt: "Migrate data"

```
I need to [add a column / rename / restructure] on the [table_name] table.

Current schema: [describe current]
New schema: [describe new]

Create:
1. A SQL migration file
2. Any code changes needed (SQLAlchemy models, agents, endpoints)
3. A rollback plan (if migration fails)
4. Test data to verify it worked
```

---

## FRONTEND (Use When Building UI)

### Prompt: "Build a component"

```
I need a React component called [ComponentName] that:
- [feature 1]
- [feature 2]
- [feature 3]

Inputs (props):
- [prop1]: [type]
- [prop2]: [type]

Outputs:
- On success: [action / what it should do]
- On error: [how to handle errors]
- On loading: [show loading state]

Build it in src/components/[ComponentName].tsx with TypeScript. Use Tailwind for styling.
Then create a simple Astro page to demo it at src/pages/demo/[component].astro.
```

### Prompt: "Fix a rendering bug"

```
The [ComponentName] component is:
- [what's wrong with rendering]

I think the issue is: [your hypothesis]

Debug:
1. Add console.logs to the render path to see what's happening
2. Check props being passed (are they correct?)
3. Check state (is it updating correctly?)
4. Verify CSS isn't hiding the component
5. Fix and show me the result

Also add a test to prevent regression.
```

### Prompt: "Connect to the API"

```
The [ComponentName] component needs to fetch data from the [/api/endpoint] endpoint.

Currently: [component doesn't fetch anything]
Should: [description of what it should fetch and display]

Add:
1. useEffect hook to fetch on mount
2. Loading state while fetching
3. Error state with retry button
4. Display the data once loaded
5. Cancel fetch if component unmounts (cleanup)

Use the fetch helper in src/utils/auth.ts (includes JWT in headers).
Test by running the actual endpoint on your local backend.
```

---

## TESTING (Use When Writing Tests)

### Prompt: "Test this function"

```
@[file_path.py#start_line-end_line]

Write comprehensive tests for the [function_name] function.

Test cases:
1. [normal input, expect normal output]
2. [edge case 1]
3. [edge case 2]
4. [error scenario 1]
5. [error scenario 2]

Use pytest. Create mocks for any external dependencies (GitHub API, Claude API, database).

File: tests/test_[module].py
Then run: pytest tests/test_[module].py -v --cov=[function_name]
```

### Prompt: "Integration test"

```
Write an end-to-end integration test that:
1. [action 1]
2. [action 2]
3. [action 3]
4. Verify final result is [expected]

This should test the real data flow (or mocked external APIs).

Use a test database (Supabase test instance or SQLite).
Setup: [describe any fixtures needed]
Cleanup: [describe what to delete after test]

File: tests/test_integration_[feature].py
```

---

## DEPLOYMENT (Use Before Deploying)

### Prompt: "Pre-deploy checklist"

```
We're about to deploy to production. Let me verify:

1. **Tests**: Run all tests, show coverage report
2. **Environment**: Check that all required env vars are documented in .env.example
3. **Dependencies**: Any new dependencies? Are they in requirements.txt?
4. **Database**: Any pending migrations? Show their status.
5. **API**: Do all endpoints have proper error handling?
6. **Frontend**: Does it build without warnings? (npm run build)
7. **Logs**: Check Sentry config is correct for production

Report on each item. Flag anything that needs fixing.
```

### Prompt: "Deploy to Railway"

```
Deploy the FastAPI backend to Railway:

1. Ensure railway.toml is configured correctly
2. Set production environment variables in Railway console (don't paste secrets here, I'll add them manually)
3. Trigger a production build
4. Show the deployment logs
5. Once live, test a real endpoint (GET /auth/me or similar)
6. Check Sentry is receiving errors
7. Report: "DEPLOYMENT COMPLETE" with live URL
```

### Prompt: "Deploy to Vercel"

```
Deploy the Astro frontend to Vercel:

1. Ensure vercel.json is configured
2. Trigger production build
3. Show build logs
4. Once live, test the frontend loads
5. Verify API proxy works (frontend → backend)
6. Test one full flow (login → dashboard)
7. Report: "DEPLOYMENT COMPLETE" with live URL
```

---

## DOCUMENTATION (Use When Explaining Code)

### Prompt: "Document this feature"

```
@[file_path.py]

Generate documentation for the [feature] feature:

1. **What it does** (1 paragraph)
2. **How to use it** (code example)
3. **Database schema** (if applicable, show CREATE TABLE)
4. **API endpoints** (if applicable, show requests/responses)
5. **Configuration** (what env vars are needed?)
6. **Known limitations** (any?)

Write it in Markdown and show me the output. I'll add it to docs/[feature].md.
```

### Prompt: "Generate API docs"

```
Extract API documentation from the FastAPI app:

1. List all endpoints (method, path, description)
2. For each endpoint:
   - Input schema (request body, query params)
   - Output schema (response JSON)
   - Error responses (400, 401, 404, 500)
   - Example curl request

Format as Markdown (I'll add it to docs/API.md).

Also, FastAPI has auto-docs at /docs. Make sure:
- All endpoints have docstrings
- All parameters are documented
- All response models are defined
```

---

## DEBUGGING LANGGRAPH (Use When Agent Orchestration Breaks)

### Prompt: "Why is the agent stuck?"

```
The team analysis started but seems stuck at stage: [stage]

It's been [time] without finishing. The last log was:
[paste log message]

Debug:
1. Is an agent hanging on an API call? (add timeouts, logs)
2. Is there a deadlock in state passing? (check LangGraph state schema)
3. Is WebSocket disconnected? (check browser console)
4. Are any dependencies (GitHub API, Claude API, database) down?

Add detailed logging to the stuck agent and re-run. Show me the new logs.
```

### Prompt: "Agent isn't producing output"

```
The [agent_name] agent should produce:
- [expected output 1]
- [expected output 2]

But it's producing: [actual output]

Trace:
1. What inputs is the agent receiving?
2. Show the logic for computing the output
3. Where's the discrepancy?
4. Fix the logic or the input
5. Verify with a test

Then integrate back into the orchestrator.
```

---

## ADVANCED: SYSTEM REDESIGN (Use When Architecture Needs Change)

### Prompt: "Redesign the X system"

```
I'm concerned about [current design]:
- [problem 1]
- [problem 2]
- [problem 3]

Current implementation:
@[relevant files]

Propose a better design:
1. What changes?
2. What stays the same?
3. What code needs rewriting?
4. How do we migrate data (if applicable)?
5. Timeline to implement?

Then help me implement it incrementally without breaking the app.
```

---

## QUICK WINS (Use for Small Tasks)

### Prompt: "Add a feature flag"

```
I want to add a feature flag for [feature_name] so I can toggle it without deploying.

Add:
1. Feature flag table in Supabase
2. Function to check if feature is enabled
3. Use it in the code at [location]
4. Show me how to toggle it

Keep it simple (just a table, one boolean column).
```

### Prompt: "Add logging"

```
I need better logging for:
- [component/agent 1]
- [component/agent 2]

Add structured logs (with timestamps, level, context) to:
1. Function entry/exit
2. Important state changes
3. External API calls (request + response)
4. Errors (with stack trace)
5. Performance metrics (duration)

Use Python's logging module (already configured). Show me example logs.
```

### Prompt: "Update dependencies"

```
Update dependencies safely:

1. Show current versions (requirements.txt)
2. Check for security vulnerabilities (safety check, if available)
3. Identify what can be safely updated
4. Update in batches (don't update everything at once)
5. Run tests after each batch
6. Report what changed and why

Constraints:
- Must be backward compatible
- Tests must pass
- Don't upgrade past major version unless intentional
```

---

## PAIR PROGRAMMING MODE (Use for Real-Time Collaboration)

### Prompt: "Pair with me on [feature]"

```
I want to build [feature] together with you. Let's pair program:

1. **Plan first**: Show me the plan (what code files, what functions)
2. **Code together**: You write one function, I review, then you continue
3. **Test as we go**: Write tests for each piece
4. **Integrate**: Once done, integrate with the rest of the system

I'll provide feedback at each step. Feel free to ask clarifying questions.

Let's start: Show me the plan for [feature].
```

---

## SAVING TIME: BATCH BUILD (Use When Building Multiple Features)

### Prompt: "Build features X, Y, Z together"

```
I have time today to build 3 features:
1. [Feature 1]
2. [Feature 2]
3. [Feature 3]

They have these dependencies:
- Feature 1 must be done first (required by 2 and 3)
- Features 2 and 3 can be done in parallel

Can you:
1. Build Feature 1 completely (with tests)
2. Build Features 2 and 3 in parallel (describe what you're doing in each)
3. Integrate them together
4. Run all tests

Chunk the work into discrete tasks. After each task, report progress.

Let's go!
```

---

## RESET & START OVER (Use If Things Get Messy)

### Prompt: "Rollback to last known good state"

```
Things are broken. Let me rollback to a working state.

Last commit that was working: [commit hash or date]

Please:
1. Show me a git diff between now and then (what changed?)
2. Reset the code to that commit
3. Run all tests to verify they pass
4. Then show me what broke since then (what needs fixing)

We'll rebuild from the working state.
```

---

## FINAL POWER MOVE: EXPLAIN THE WHOLE THING

### Prompt: "Explain GitSyntropy to me like I'm an interviewer"

```
Explain the entire GitSyntropy project:

1. **The problem**: What problem does it solve?
2. **The solution**: How does GitSyntropy solve it?
3. **Technical architecture**: (5-minute explanation, not 30 minutes)
4. **The agentic difference**: Why LangGraph? Why Synthesis Agent?
5. **Key algorithms**: (Chronotype detection, Ashtakoot scoring, Monte Carlo sim)
6. **Deployment**: Where does it run? How is it scaled?
7. **The story**: Why is this interesting? Why did you build it?

Keep it interview-ready (impress someone in 10 minutes). Then ask: "Anything I missed?"
```

---

## NOTES

- **Copy-paste these**: They're templates. Customize the [brackets].
- **One prompt at a time**: Don't send 5 prompts at once. Wait for Claude to finish.
- **Ask follow-ups**: If Claude's answer is unclear, ask more questions.
- **Trust the process**: Claude will ask clarifying questions if it needs them.
- **Save your best prompts**: If you invent a good prompt, add it to this file for next time.

Good luck! 🚀
