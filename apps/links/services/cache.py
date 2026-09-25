import logging
import random
from typing import Optional

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


def get_redis_client():
    """
    Creates and returns a Redis client.
    """
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )


def get_cached_url(short_code: str) -> Optional[str]:
    """
    Returns cached URL data.

    Returns:
        - URL string if cache hit
        - "__404__" if negative cache hit
        - None if cache miss or Redis unavailable
    """

    key = f"short:{short_code}"

    try:
        client = get_redis_client()
        return client.get(key)

    except redis.RedisError as exc:
        logger.warning(
            "Redis unavailable while reading key %s: %s",
            key,
            exc,
        )
        return None


def cache_url(
    short_code: str,
    original_url: str,
) -> bool:
    """
    Stores a URL in Redis with TTL jitter.
    """

    key = f"short:{short_code}"

    base_ttl = settings.CACHE_TTL_SECONDS
    jitter_pct = settings.CACHE_TTL_JITTER_PCT

    jitter = int(base_ttl * jitter_pct / 100)

    ttl = random.randint(
        base_ttl - jitter,
        base_ttl + jitter,
    )

    try:
        client = get_redis_client()

        client.set(
            key,
            original_url,
            ex=ttl,
        )

        return True

    except redis.RedisError as exc:
        logger.warning(
            "Redis unavailable while caching key %s: %s",
            key,
            exc,
        )
        return False


def cache_not_found(short_code: str) -> bool:
    """
    Stores a negative-cache entry for a short period.

    This prevents repeated database queries
    for non-existent short codes.
    """

    key = f"short:{short_code}"

    try:
        client = get_redis_client()

        client.set(
            key,
            settings.NEGATIVE_CACHE_SENTINEL,
            ex=settings.NEGATIVE_CACHE_TTL_SECONDS,
        )

        return True

    except redis.RedisError as exc:
        logger.warning(
            "Redis unavailable while caching negative result %s: %s",
            key,
            exc,
        )
        return False