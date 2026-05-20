import logging

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client: Redis | None = None


def _is_valid_redis_url(redis_url: str) -> bool:
    return redis_url.startswith(("redis://", "rediss://"))


async def init_redis() -> None:
    global redis_client
    if not settings.redis_url:
        logger.warning("REDIS_URL is not configured; redis disabled")
        return
    if not _is_valid_redis_url(settings.redis_url):
        logger.warning("REDIS_URL is invalid; redis disabled")
        return

    redis_client = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


async def close_redis() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


def get_redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis is not configured")
    return redis_client


async def check_redis() -> bool:
    if redis_client is None:
        return False
    try:
        return bool(await redis_client.ping())
    except Exception:
        logger.exception("Redis health check failed")
        return False
