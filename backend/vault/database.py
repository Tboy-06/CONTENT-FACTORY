from __future__ import annotations

import contextlib
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.config import get_settings
from backend.vault.models import Base

settings = get_settings()

engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def init_database() -> None:
    global engine, async_session_factory

    db_url = settings.effective_database_url

    # SQLite needs special handling for async
    if db_url.startswith("sqlite"):
        # Convert to aiosqlite
        if not db_url.startswith("sqlite+aiosqlite"):
            db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
        connect_args = {"check_same_thread": False}
        poolclass = NullPool
    else:
        connect_args = {}
        poolclass = None

    engine = create_async_engine(
        db_url,
        echo=settings.log_level == "DEBUG",
        connect_args=connect_args,
        poolclass=poolclass,
    )

    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


async def create_tables() -> None:
    if engine is None:
        init_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    if engine is None:
        init_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@contextlib.asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if async_session_factory is None:
        init_database()
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextlib.asynccontextmanager
async def get_session_no_commit() -> AsyncGenerator[AsyncSession, None]:
    if async_session_factory is None:
        init_database()
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()