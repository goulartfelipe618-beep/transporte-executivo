"""Optional Redis cache."""

from typing import Any, Optional

from app.config import get_settings

settings = get_settings()
_redis = None


async def get_redis():
    global _redis
    if not settings.redis_enabled:
        return None
    if _redis is None:
        import redis.asyncio as aioredis

        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def cache_get(key: str) -> Optional[str]:
    client = await get_redis()
    if not client:
        return None
    return await client.get(key)


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    client = await get_redis()
    if client:
        await client.setex(key, ttl, value)
