# GitSyntropy — LLM Handoff Prompt

Copy everything below this line and paste it as your first message in a new chat.

---

## Context

You are helping me continue development on **GitSyntropy**, a production web app that predicts team compatibility by combining GitHub behavioral data with psychometric profiling. The system runs a multi-agent pipeline (LangGraph) that produces a Claude-synthesised narrative report about how well a team of developers will work together.

**Repo owner:** GitHub handle `1mystic`  
**Current date context:** April 2026  

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.12), SQLAlchemy 2.0 async, asyncpg |
| Database | Supabase (PostgreSQL) — hosted, already provisioned |
| AI pipeline | LangGraph orchestrator → Anthropic Claude (`claude-sonnet-4-6`) streaming |
| GitHub data | PyGithub + custom `GitHubAnalystClient`, K-Means chronotype clustering |
| Auth | GitHub OAuth 2.0 → JWT (python-jose), stored in localStorage |
| Rate limiting | slowapi (200/min default, tighter on auth/sync endpoints) |
| Frontend | Astro 4 (static output) + React islands (`client:load`) |
| State | nanostores (`$session`, `$sync`, `$teams`, etc.) |
| Styling | Tailwind CSS, custom glass-panel design system, Framer Motion |
| Deployment | Render (backend, free tier) + Vercel (frontend, free tier) |

---

## Project Structure

```
GitSyntropy/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py        # FastAPI app, all endpoints
│   │   │   ├── models.py      # SQLAlchemy ORM models
│   │   │   ├── schemas.py     # Pydantic request/response schemas
│   │   │   ├── services.py    # Business logic, JWT, GitHub sync, assessment
│   │   │   ├── config.py      # pydantic-settings (GS_ env prefix)
│   │   │   ├── database.py    # async engine, create_tables()
│   │   │   ├── github_client.py  # GitHubAnalystClient (PyGithub)
│   │   │   └── claude_client.py  # Anthropic streaming client
│   │   ├── tests/             # pytest, 84 tests, ~83% coverage
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── .python-version    # 3.12.0 (pins for Render)
│   │   ├── render.yaml        # Render deployment config
│   │   └── .env               # local only, gitignored
│   └── frontend/
│       ├── src/
│       │   ├── pages/         # auth, dashboard, workspace, compatibility,
│       │   │                  # assessment, insights, admin, index, guide, report
│       │   ├── components/
│       │   │   ├── AuthClient.tsx       # GitHub OAuth + email login
│       │   │   ├── DashboardClient.tsx  # main dashboard, GitHub sync, orchestrator
│       │   │   ├── WorkspaceClient.tsx  # team management + LangGraph run
│       │   │   ├── InsightsClient.tsx   # Claude streaming narrative
│       │   │   ├── CompatibilityClient.tsx
│       │   │   ├── AssessmentClient.tsx # adaptive CAT questionnaire
│       │   │   ├── AdminClient.tsx      # superadmin panel (1mystic only)
│       │   │   ├── ProtectedGate.tsx    # auth guard + guest trial mode
│       │   │   ├── NavUser.tsx          # sidebar user avatar/sign-out island
│       │   │   ├── SideNav.astro        # sidebar nav
│       │   │   ├── RadarChart.tsx
│       │   │   └── ChronotypeHeatmap.tsx
│       │   └── lib/
│       │       ├── api.ts           # all fetch calls to backend
│       │       ├── stores.ts        # nanostores (Session, SyncState, etc.)
│       │       └── featureFlags.ts  # AUTH_REQUIRED, GUEST_TRIAL_ENABLED
│       ├── vercel.json
│       └── .env.example
└── .github/workflows/ci.yml   # backend pytest + frontend build
```

---

## Database Models (Supabase / SQLAlchemy)

| Table | Purpose |
|-------|---------|
| `user_profiles` | One row per OAuth user — github_handle, avatar, email, last_seen_at |
| `github_profiles` | Per-user GitHub sync results — chronotype, activity scores, PR/commit counts |
| `psychometric_profiles` | Assessment answers + 8-dimension scores |
| `agent_runs` | LangGraph orchestrator run log |
| `teams` | Team records |
| `team_members` | Many-to-many users ↔ teams |
| `team_scores` | Versioned Ashtakoot compatibility scores per run |

Tables are created automatically via `Base.metadata.create_all` on startup (no manual migrations needed for new tables).

---

## API Endpoints (all prefixed `/api/v1`)

```
GET  /health
POST /auth/github/callback    → AuthTokenResponse (includes github_handle, avatar, is_superadmin)
GET  /auth/github/start       → GithubAuthStartResponse
POST /auth/login              → AuthTokenResponse (email fallback)
GET  /auth/session            → AuthSessionResponse
GET  /users/me                → UserProfileResponse
POST /github/sync             → GithubSyncResponse
GET  /github/sync/{sync_id}
GET  /assessment/questions
POST /assessment/responses
POST /assessment/cat/next     → CAT adaptive next question
POST /compatibility/run
POST /orchestrator/run        → kicks off LangGraph pipeline
GET  /insights/synthesis
POST /teams  /  GET /teams
GET/PATCH /teams/{id}
POST /teams/{id}/members  /  DELETE /teams/{id}/members/{user_id}
POST /candidates/simulate     → Monte Carlo (1000 iterations)
GET  /admin/stats             → superadmin only (403 otherwise)
GET  /admin/users             → superadmin only
WS   /ws/analysis/{run_id}    → LangGraph step streaming + Claude token streaming
```

---

## Auth Flow

1. Frontend calls `GET /auth/github/start` → gets `authorization_url` + `state`
2. State saved to `sessionStorage`, browser redirected to GitHub
3. GitHub redirects back to `/auth?code=...`
4. Frontend calls `POST /auth/github/callback` with code+state
5. Backend exchanges code → GitHub user API → upserts `user_profiles` row → returns JWT + profile
6. JWT stored in localStorage as `gitsyntropy.session`
7. Session includes: `userId`, `token`, `githubHandle`, `githubName`, `githubAvatarUrl`, `isSuperadmin`

---

## Superadmin

- GitHub handle: `1mystic`
- Email: `23f2004201@ss.com`
- Controlled by `GS_SUPERADMIN_GITHUB_HANDLE` env var (backend)
- `is_superadmin(github_handle)` checked in JWT claims
- Routes `/api/v1/admin/*` return 403 for non-admins
- Frontend `/admin` page shows "Access Denied" if `session.isSuperadmin !== true`

---

## Feature Flags (frontend env vars)

| Var | Default (prod) | Effect |
|-----|---------------|--------|
| `PUBLIC_AUTH_REQUIRED` | `true` | Enforce login on app pages |
| `PUBLIC_GUEST_TRIAL` | `true` | Show demo data + banner to unauthenticated visitors instead of hard-blocking |

---

## Compatibility Scoring System

8 dimensions (originally Vedic, renamed to English industry metrics):

| Internal key | Display label |
|-------------|--------------|
| `varna_alignment` | Innovation Drive |
| `vashya_influence` | Leadership Orientation |
| `tara_resilience` | Team Resilience |
| `yoni_workstyle` | Work Style |
| `graha_maitri_cognition` | Decision Style |
| `gana_temperament` | Risk Tolerance |
| `bhakoot_strategy` | Stress Response |
| `nadi_chronotype_sync` | Chronotype Sync |

Weights: 1–8 (nadi highest). Total max score = 36. `score_pct_100 = total/36*100`.

---

## Deployment Status

| Service | Platform | URL | Status |
|---------|----------|-----|--------|
| Backend | Render (free) | `https://gitsyntropy-api.onrender.com` | Deploying — see issues below |
| Frontend | Vercel (free) | `https://gitsyntropy.vercel.app` | Deploying — see issues below |
| Database | Supabase | `baiisauubbaowenlzefh.supabase.co` | Live |

**Recently fixed (last session):**
- Render was picking Python 3.14 → added `.python-version: 3.12.0`
- Vercel crashed with `No QueryClient set` during SSR → rewrote `ProtectedGate` to use `useEffect`+`useState` instead of `useQuery` (each Astro island is an isolated React tree with no shared `QueryClientProvider`)

**Still needed to complete deployment:**
1. Supabase DB password → paste into Render `GS_DATABASE_URL` env var
2. `GS_GITHUB_CLIENT_SECRET` → paste from `apps/backend/.env` into Render
3. `GS_ANTHROPIC_API_KEY` → paste from `apps/backend/.env` into Render
4. After Vercel gives real domain → update Render vars `GS_FRONTEND_URL` + `GS_GITHUB_REDIRECT_URL`
5. After Render gives real domain → update Vercel vars `PUBLIC_API_BASE` + `PUBLIC_WS_BASE`
6. Update GitHub OAuth App callback URL to `https://<vercel-domain>/auth`
7. (Optional) Add UptimeRobot ping to `/api/v1/health` every 10 min to prevent Render free-tier sleep

**Local dev note:** GitHub OAuth needs a separate dev OAuth App with callback `http://localhost:4321/auth` — the production app's callback is set to the Vercel domain.

---

## Known Gaps / Not Yet Done

- `GS_GITHUB_ACCESS_TOKEN` not set → GitHub sync uses deterministic mock data (not real API)
- CI secrets not yet added to GitHub repo (`GS_DATABASE_URL`, `GS_ANTHROPIC_API_KEY`)
- Assessment submission is disabled in guest mode (intentional — no saving without login)
- No email-based auth in production (email login is a dev convenience endpoint only)

---

You now have full context. What would you like to work on?


render failure latest 

ERROR:    Application startup failed. Exiting.
Menu
==> Exited with status 3
==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys
==> Running 'uvicorn app.main:app --host 0.0.0.0 --port $PORT'
==> No open ports detected, continuing to scan...
==> Docs on specifying a port: https://render.com/docs/web-services#port-binding
INFO:     Started server process [49]
INFO:     Waiting for application startup.
ERROR:    Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 526, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 773, in _prepare
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/asyncpg/connection.py", line 638, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/asyncpg/connection.py", line 657, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/asyncpg/connection.py", line 443, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg/protocol/protocol.pyx", line 165, in prepare
asyncpg.exceptions.DuplicatePreparedStatementError: prepared statement "__asyncpg_stmt_1__" already exists
HINT:  
NOTE: pgbouncer with pool_mode set to "transaction" or
"statement" does not support prepared statements properly.
You have two options:
* if you are using pgbouncer for connection pooling to a
  single server, switch to the connection pool functionality
  provided by asyncpg, it is a much better option for this
  purpose;
* if you have no option of avoiding the use of pgbouncer,
  then you can set statement_cache_size to 0 when creating
  the asyncpg connection object.
The above exception was the direct cause of the following exception:
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.DuplicatePreparedStatementError'>: prepared statement "__asyncpg_stmt_1__" already exists
HINT:  
NOTE: pgbouncer with pool_mode set to "transaction" or
"statement" does not support prepared statements properly.
You have two options:
* if you are using pgbouncer for connection pooling to a
  single server, switch to the connection pool functionality
  provided by asyncpg, it is a much better option for this
  purpose;
* if you have no option of avoiding the use of pgbouncer,
  then you can set statement_cache_size to 0 when creating
  the asyncpg connection object.
The above exception was the direct cause of the following exception:
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/starlette/routing.py", line 638, in lifespan
    async with self.lifespan_context(app) as maybe_state:
  File "/opt/render/project/python/Python-3.12.0/lib/python3.12/contextlib.py", line 204, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/apps/backend/app/main.py", line 94, in lifespan
    await create_tables()
  File "/opt/render/project/src/apps/backend/app/database.py", line 30, in create_tables
    async with engine.begin() as conn:
  File "/opt/render/project/python/Python-3.12.0/lib/python3.12/contextlib.py", line 204, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/engine.py", line 1068, in begin
    async with conn:
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/base.py", line 121, in __aenter__
    return await self.start(is_ctxmanager=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/engine.py", line 275, in start
    await greenlet_spawn(self.sync_engine.connect)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 203, in greenlet_spawn
    result = context.switch(value)
             ^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 3293, in connect
    return self._connection_cls(self)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 143, in __init__
    self._dbapi_connection = engine.raw_connection()
                             ^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 3317, in raw_connection
    return self.pool.connect()
           ^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 448, in connect
    return _ConnectionFairy._checkout(self)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 1272, in _checkout
    fairy = _ConnectionRecord.checkout(pool)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 712, in checkout
    rec = pool._do_get()
          ^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/pool/impl.py", line 177, in _do_get
    with util.safe_reraise():
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/util/langhelpers.py", line 121, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/pool/impl.py", line 175, in _do_get
    return self._create_connection()
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 389, in _create_connection
    return _ConnectionRecord(self)
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 674, in __init__
    self.__connect()
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 914, in __connect
    )._exec_w_sync_on_first_run(self.dbapi_connection, self)
      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/event/attr.py", line 501, in _exec_w_sync_on_first_run
    self(*args, **kw)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/event/attr.py", line 515, in __call__
    fn(*args, **kw)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/util/langhelpers.py", line 1897, in go
    return once_fn(*arg, **kw)
           ^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/create.py", line 773, in first_connect
    dialect.initialize(c)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/base.py", line 3340, in initialize
    super().initialize(connection)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 528, in initialize
    self.server_version_info = self._get_server_version_info(
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/base.py", line 3610, in _get_server_version_info
    v = connection.exec_driver_sql("select pg_catalog.version()").scalar()
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1779, in exec_driver_sql
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/opt/render/project/src/.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.DuplicatePreparedStatementError'>: prepared statement "__asyncpg_stmt_1__" already exists
HINT:  
NOTE: pgbouncer with pool_mode set to "transaction" or
"statement" does not support prepared statements properly.
You have two options:
* if you are using pgbouncer for connection pooling to a
  single server, switch to the connection pool functionality
  provided by asyncpg, it is a much better option for this
  purpose;
* if you have no option of avoiding the use of pgbouncer,
  then you can set statement_cache_size to 0 when creating
  the asyncpg connection object.
[SQL: select pg_catalog.version()]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:    Application startup failed. Exiting.