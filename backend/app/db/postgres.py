import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def _is_valid_database_url(database_url: str) -> bool:
    return database_url.startswith(("postgresql://", "postgresql+asyncpg://"))


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlsplit(database_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    sslmode = query.pop("sslmode", None)
    if sslmode and "ssl" not in query:
        query["ssl"] = "require" if sslmode == "require" else sslmode

    return urlunsplit(parsed._replace(query=urlencode(query)))


async def init_db() -> None:
    global engine, SessionLocal
    if not settings.database_url:
        logger.warning("DATABASE_URL is not configured; database disabled")
        return
    if not _is_valid_database_url(settings.database_url):
        logger.warning("DATABASE_URL is invalid; database disabled")
        return

    engine = create_async_engine(
        _normalize_database_url(settings.database_url),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        pool_timeout=settings.database_connect_timeout_seconds,
        connect_args={
            "timeout": settings.database_connect_timeout_seconds,
            "command_timeout": settings.database_connect_timeout_seconds,
        },
    )
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def close_db() -> None:
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None


async def get_db() -> AsyncSession:
    if SessionLocal is None:
        raise RuntimeError("Database is not configured")
    async with SessionLocal() as session:
        yield session


async def check_db() -> bool:
    if engine is None:
        return False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False
