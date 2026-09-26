import logging
import time
from typing import Tuple

import redis
from django.conf import settings
from rest_framework.request import Request

from apps.links.services.cache import get_redis_client

logger = logging.getLogger(__name__)

# Atomic Fixed-Window Rate Limiting Lua Script
# KEYS[1] = "rl:{action}:{ip}:{window_start}"
# ARGV[1] = window_duration_in_seconds (e.g. 60)
#
# Logic:
# 1. INCR the key.
# 2. If value is 1, set EXPIRE to window_duration + 1s buffer.
# 3. Return current count and remaining TTL.
LUA_RATE_LIMIT_SCRIPT = """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
    redis.call("EXPIRE", KEYS[1], tonumber(ARGV[1]) + 1)
end
local ttl = redis.call("TTL", KEYS[1])
return {current, ttl}
"""


def get_client_ip(request: Request) -> str:
    """
    Safely resolves client IP address.

    Security Rule:
    Never blindly trust the leftmost entry of X-Forwarded-For because clients can spoof it.
    If NUM_PROXIES > 0, we take the IP from the rightmost trusted hop.
    Otherwise, we use request.META['REMOTE_ADDR'].
    """
    num_proxies = getattr(settings, "NUM_PROXIES", 0)

    if num_proxies > 0 and "HTTP_X_FORWARDED_FOR" in request.META:
        forwarded_ips = [
            ip.strip() for ip in request.META["HTTP_X_FORWARDED_FOR"].split(",")
        ]
        if len(forwarded_ips) >= num_proxies:
            return forwarded_ips[-num_proxies]

    return request.META.get("REMOTE_ADDR", "127.0.0.1")


def check_rate_limit(
    key_identifier: str,
    action: str = "create",
    limit: int = 100,
    window_seconds: int = 60,
) -> Tuple[bool, int, int]:
    """
    Evaluates rate limit atomically using Redis.

    Returns:
        (is_allowed: bool, remaining_requests: int, reset_seconds: int)
    """
    # Align window to fixed epoch interval (e.g. 60-second boundaries)
    current_time = int(time.time())
    window_start = (current_time // window_seconds) * window_seconds
    redis_key = f"rl:{action}:{key_identifier}:{window_start}"

    client = get_redis_client()

    try:
        # Atomic execution inside Redis
        result = client.eval(
            LUA_RATE_LIMIT_SCRIPT,
            1,
            redis_key,
            window_seconds,
        )
        current_count = int(result[0])
        ttl = int(result[1])

        # TTL can be -1 or -2 if expired; clamp to window
        reset_seconds = max(ttl, 1)
        remaining = max(0, limit - current_count)
        is_allowed = current_count <= limit

        return is_allowed, remaining, reset_seconds

    except redis.RedisError as exc:
        logger.warning(
            "rate_limit_redis_failure_failing_open",
            extra={"key": key_identifier, "error": str(exc)},
        )
        # Fail-open behavior: allow request if Redis is down
        if getattr(settings, "RATE_LIMIT_FAIL_OPEN", True):
            return True, limit, 0
        # Fail-closed behavior (if configured)
        return False, 0, window_seconds