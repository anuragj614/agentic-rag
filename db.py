from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import HTTPException, Request
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from settings import settings
from utils.logger import get_logger

logger = get_logger()


class SessionManager:
    """Manages asynchronous DB sessions with connection pooling."""

    def __init__(self) -> None:
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    def init_db(self) -> None:
        """Initialize the database engine and session factory."""

        self.engine = create_async_engine(
            settings.DB_URL,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=False,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession,
        )

    async def close(self) -> None:
        """Dispose of the database engine."""
        if self.engine:
            await self.engine.dispose()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield a database session."""
        if not self.session_factory:
            raise RuntimeError("Database session factory not initialized.")

        async with self.session_factory() as session:
            try:
                yield session
            except HTTPException:
                await session.rollback()
                raise
            except ValueError as ve:
                logger.exception("ValueError: %s", ve)
                await session.rollback()
                raise ve
            except AttributeError as ae:
                logger.exception("AttributeError: %s", ae)
                await session.rollback()
                raise ae
            except Exception as e:
                logger.exception("UnexpectedError: %s", e)
                await session.rollback()
                raise e


# Global instances
sessionmanager = SessionManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session."""

    async with sessionmanager.get_session() as session:
        yield session


async def get_redis(request: Request) -> Redis:
    """Dependency to get Redis from app state."""
    return request.app.state.redis
