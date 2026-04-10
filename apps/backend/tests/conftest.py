"""Pytest configuration: override get_db with a NullPool engine for all tests.

NullPool creates a fresh asyncpg connection per request instead of reusing pooled
connections across different event-loop instances (which causes asyncpg ping errors
when the TestClient runs requests in a thread with a fresh event loop).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import get_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def override_db_dependency():
    """Session-wide DB override: NullPool so each request gets a fresh connection."""
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)

    async def _get_test_db():
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()
