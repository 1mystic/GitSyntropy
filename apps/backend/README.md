# GitSyntropy Backend

## Run locally

1. `python -m venv .venv`
2. `.venv\\Scripts\\activate`
3. `pip install -e .[dev]`
4. `uvicorn app.main:app --reload --port 8000`

By default the backend uses a local SQLite database file (`gitsyntropy_local.db`) so you can run
the app without PostgreSQL. Set `GS_DATABASE_URL` only if you want to point at Supabase or another
Postgres instance.

## Test

- `pytest`

## API root

- `http://localhost:8000/api/v1/health`
