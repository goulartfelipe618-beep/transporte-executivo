"""Database session and engine — inicializacao lazy."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

_engine = None
_async_session_factory = None


class Base(DeclarativeBase):
    pass


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url.strip():
            raise RuntimeError(
                "DATABASE_URL nao configurada. Defina no EasyPanel (Environment Variables)."
            )
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_async_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_factory


def __getattr__(name: str):
    if name == "engine":
        return get_engine()
    if name == "AsyncSessionLocal":
        return get_async_session_factory()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
