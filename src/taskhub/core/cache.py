"""Redis caching infrastructure and helper utilities with graceful degradation."""

import json
import logging
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from taskhub.core.config import settings

logger = logging.getLogger("taskhub.cache")

_redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """Lazily initialize and return the global async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close active Redis client connection pool."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception as e:
            logger.warning("Error while closing Redis connection: %s", e)
        finally:
            _redis_client = None


def build_project_tasks_cache_key(
    project_id: int,
    status: Any = None,
    priority: Any = None,
    assignee_id: int | None = None,
    offset: int = 0,
    limit: int = 20,
) -> str:
    """Build normalized Redis cache key for project tasks query."""
    status_val = (
        status.value if hasattr(status, "value") else str(status) if status is not None else "None"
    )
    priority_val = (
        priority.value
        if hasattr(priority, "value")
        else str(priority)
        if priority is not None
        else "None"
    )
    assignee_val = str(assignee_id) if assignee_id is not None else "None"
    return (
        f"tasks:project:{project_id}:status:{status_val}:priority:{priority_val}:"
        f"assignee:{assignee_val}:offset:{offset}:limit:{limit}"
    )


async def get_cache(key: str) -> Any | None:
    """Fetch and deserialize JSON value from Redis with graceful degradation."""
    try:
        client = get_redis_client()
        raw = await client.get(key)
        if raw is not None:
            return json.loads(raw)
        return None
    except (RedisError, Exception) as e:
        logger.warning("Redis get_cache error for key '%s': %s", key, e)
        return None


async def set_cache(key: str, value: Any, ttl: int = settings.CACHE_TTL_SECONDS) -> None:
    """Serialize and store value in Redis with TTL and graceful degradation."""
    try:
        client = get_redis_client()
        serialized = json.dumps(value, default=str)
        await client.set(key, serialized, ex=ttl)
    except (RedisError, Exception) as e:
        logger.warning("Redis set_cache error for key '%s': %s", key, e)


async def invalidate_project_tasks_cache(project_id: int) -> None:
    """Invalidate all task query cache keys matching the given project ID."""
    try:
        client = get_redis_client()
        pattern = f"tasks:project:{project_id}:*"
        keys: list[str] = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await client.delete(*keys)
    except (RedisError, Exception) as e:
        logger.warning("Redis invalidation failed for project %s: %s", project_id, e)
