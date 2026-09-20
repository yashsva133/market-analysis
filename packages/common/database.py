"""Database connection and request-scoped transactions."""
from typing import AsyncGenerator
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from .config import settings
from .logging import get_logger

logger = get_logger(__name__)
Base = declarative_base()
database_url = settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1).replace("postgresql://", "postgresql+asyncpg://", 1)
engine = create_async_engine(database_url, pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW, pool_pre_ping=True,
    connect_args={"timeout": 10, "command_timeout": 30})
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession,
    expire_on_commit=False, autocommit=False, autoflush=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError, TimeoutError) as exc:
            logger.error("Database connection failed: %s", type(exc).__name__)
            raise HTTPException(503, detail={"status": "UNAVAILABLE", "code": "DATABASE_UNAVAILABLE", "message": "PostgreSQL is unreachable. Check database configuration and connectivity; no sample data is substituted."}) from exc
        try:
            yield session
            await session.commit()
        except HTTPException:
            await session.rollback()
            raise
        except (SQLAlchemyError, OSError, TimeoutError) as exc:
            await session.rollback()
            logger.error("Database operation failed: %s", type(exc).__name__)
            raise HTTPException(503, detail={"status": "FAILED", "code": "DATABASE_QUERY_FAILED", "message": "Database operation failed. Check backend logs using the request correlation ID."}) from exc
        except Exception:
            await session.rollback()
            raise
