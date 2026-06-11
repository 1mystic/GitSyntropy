"""Pytest configuration: use SQLite in-memory DB so no PostgreSQL is needed in CI.

aiosqlite is used as the async driver. Tables are created once per session and
shared across all tests (individual tests should use unique user/team IDs to
avoid cross-test interference).
"""

import asyncio
import sqlite3

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services import create_jwt

# Keepalive: a shared-cache in-memory SQLite database only lives while at least one
# connection to it is open. pytest-asyncio (asyncio_mode = "auto") runs each async
# test in its own event loop and closes it afterwards, which would otherwise tear
# down the async connection and drop the DB ("no such table" in a later test). This
# module-level synchronous connection stays open for the whole process, pinning the
# shared-cache DB so the schema created below survives across every test's loop.
_DB_URI = "file:gitsyntropy_test?mode=memory&cache=shared"
_KEEPALIVE = sqlite3.connect(_DB_URI, uri=True, check_same_thread=False)

# Single shared in-memory SQLite engine for the entire test session.
#
# We use a *named shared-cache* in-memory database rather than the bare ":memory:"
# form. With asyncio_mode = "auto", pytest-asyncio runs each async test in its own
# event loop and closes it afterwards; a bare ":memory:" DB is bound to the single
# StaticPool connection's original loop, so once that loop closes a later test can
# observe an empty DB ("no such table"). A shared-cache DB (cache=shared) survives
# as long as any connection stays open (StaticPool keeps one), and every connection
# — regardless of which loop opened it — sees the same tables. This removes the
# test-ordering fragility entirely.
_TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///file:gitsyntropy_test?mode=memory&cache=shared&uri=true",
    connect_args={"check_same_thread": False, "uri": True},
    poolclass=StaticPool,
)


def _run_sync(coro):
    """Run a coroutine synchronously (safe to call from sync fixtures)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture(scope="session", autouse=True)
def override_db_dependency():
    """Session-wide DB override: SQLite in-memory, tables created once."""
    async def _init():
        async with _TEST_ENGINE.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    _run_sync(_init())

    async def _get_test_db():
        async with AsyncSession(_TEST_ENGINE, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def auth_headers():
    token, _ = create_jwt(user_id="test_user", github_handle="test_handle")
    return {"Authorization": f"Bearer {token}"}
