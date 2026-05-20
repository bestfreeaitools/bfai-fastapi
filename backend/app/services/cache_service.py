import json
import logging
from typing import Any

from app.db import redis

logger = logging.getLogger(__name__)


class CacheService:
    async def get_json(self, key: str) -> dict[str, Any] | None:
        if redis.redis_client is None:
            return None

        try:
            value = await redis.redis_client.get(key)
        except Exception:
            logger.exception("Redis cache read failed", extra={"cache_key": key})
            return None

        if not value:
            return None

        logger.info("Cache hit", extra={"cache_key": key})
        return json.loads(value)

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        if redis.redis_client is None:
            return

        try:
            await redis.redis_client.set(key, json.dumps(value), ex=ttl_seconds)
        except Exception:
            logger.exception("Redis cache write failed", extra={"cache_key": key})


def get_cache_service() -> CacheService:
    return CacheService()
