import json
import logging
import random

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)

def build_short_url_cache_key(short_code: str) -> str:
    """
    Build the Redis key for a short URL.
    """
    return f"short:{short_code}"


def calculate_ttl_with_jitter(
    base_ttl: int,
    jitter_pct: int,
) -> int:
    """
    Calculate TTL with random +/- jitter.

    Example:
        base_ttl = 86400
        jitter_pct = 10

        Result:
        77760 to 95040 seconds
    """

    jitter = random.uniform(
        -jitter_pct,
        jitter_pct,
    ) / 100

    return int(base_ttl * (1 + jitter))


def get_redis_client():
    """
    Return the Redis client.
    """
    return redis_client


def get_cached_url_data(short_code: str):
    """
    Returns cached URL data.

    Returns:
        dict       -> cache hit
        "__404__"  -> negative cache hit
        None       -> cache miss / Redis unavailable
    """

    key = build_short_url_cache_key(short_code)

    try:
        value = redis_client.get(key)

        if value is None:
            return None

        if value == settings.NEGATIVE_CACHE_SENTINEL:
            return value

        return json.loads(value)

    except redis.RedisError as exc:
        logger.warning(
            "Redis GET failed: %s",
            exc,
        )
        return None


def cache_url(
    short_code: str,
    original_url: str,
    is_active: bool,
    expires_at,
):
    """
    Store URL information in Redis with TTL jitter.
    """

    key = build_short_url_cache_key(short_code)

    payload = {
        "original_url": original_url,
        "is_active": is_active,
        "expires_at": (
            expires_at.isoformat()
            if expires_at
            else None
        ),
    }

    ttl = calculate_ttl_with_jitter(
        settings.CACHE_TTL_SECONDS,
        settings.CACHE_TTL_JITTER_PCT,
    )

    try:
        redis_client.setex(
            key,
            ttl,
            json.dumps(payload),
        )

    except redis.RedisError as exc:
        logger.warning(
            "Redis SET failed: %s",
            exc,
        )


def cache_not_found(short_code: str):
    """
    Negative cache for non-existent short codes.
    """

    key = build_short_url_cache_key(short_code)

    try:
        redis_client.setex(
            key,
            settings.NEGATIVE_CACHE_TTL_SECONDS,
            settings.NEGATIVE_CACHE_SENTINEL,
        )

    except redis.RedisError as exc:
        logger.warning(
            "Redis negative cache failed: %s",
            exc,
        )


def delete_cached_url(short_code: str):
    """
    Delete cached short URL.
    Useful later for cache invalidation.
    """

    key = build_short_url_cache_key(short_code)

    try:
        redis_client.delete(key)

    except redis.RedisError as exc:
        logger.warning(
            "Redis DELETE failed: %s",
            exc,
        )