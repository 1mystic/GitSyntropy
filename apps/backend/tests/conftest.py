"""Pytest configuration: use SQLite in-memory DB so no PostgreSQL is needed in CI.

aiosqlite is used as the async driver. Tables are created once per session and
shared across all tests (individual tests should use unique user/team IDs to
avoid cross-test interference).
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Single shared in-memory SQLite engine for the entire test session.
# StaticPool + check_same_thread=False ensures the same in-memory DB is reused
# across all requests in the test session.
_TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
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
