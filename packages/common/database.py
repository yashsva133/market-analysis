"""Database connection and session lifecycle management."""
import time
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

# Base class for SQLAlchemy ORM models
Base = declarative_base()

# Async Engine with fast connection timeout
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    connect_args={"timeout": 0.5, "command_timeout": 3.0},
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Circuit breaker state for standalone / offline DB deployments
_DB_COOLOFF_UNTIL: float = 0.0


def _is_db_cooling_down() -> bool:
    global _DB_COOLOFF_UNTIL
    return time.time() < _DB_COOLOFF_UNTIL


def _record_db_failure(cooloff_seconds: float = 15.0):
    global _DB_COOLOFF_UNTIL
    _DB_COOLOFF_UNTIL = time.time() + cooloff_seconds


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session per request/task."""
    if _is_db_cooling_down():
        raise RuntimeError("Database is offline or cooling down; operating in standalone resilient mode")

    try:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    except Exception as exc:
        _record_db_failure(15.0)
        raise

