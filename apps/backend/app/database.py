import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "statement_cache_size": 0,
        "timeout": 30,           # asyncpg per-connection timeout (seconds)
        "command_timeout": 30,   # per-query timeout
    },
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables() -> None:
    """Create all tables on startup if they don't exist.

    Retries up to 5 times with exponential backoff so a transient Supabase
    connection timeout on Render cold-start doesn't kill the process.
    """
    for attempt in range(1, 6):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables verified/created successfully.")
            return
        except Exception as exc:
            wait = 2 ** attempt  # 2, 4, 8, 16, 32 seconds
            logger.warning(
                "create_tables attempt %d/5 failed (%s: %s). Retrying in %ds…",
                attempt, type(exc).__name__, exc, wait,
            )
            if attempt < 5:
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "create_tables failed after 5 attempts — tables may already exist, "
                    "continuing startup. Error: %s", exc
                )
