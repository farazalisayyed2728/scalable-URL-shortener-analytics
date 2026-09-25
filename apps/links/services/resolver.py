from datetime import datetime
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.core.exceptions import LinkExpiredException, LinkNotFoundException
from apps.links.models import ShortURL
from .cache import (
    get_cached_url_data,
    cache_url,
    cache_not_found,
)




def _check_link_state(is_active: bool, expires_at: datetime | None) -> None:
    """Validates link state flags and expiration constraints."""
    if not is_active:
        raise LinkExpiredException(message="This short link has been disabled.")

    if expires_at is not None and timezone.now() >= expires_at:
        raise LinkExpiredException(message="This short link has expired.")


def resolve_short_code(short_code: str) -> str:
    """
    Resolves short_code via Cache-Aside strategy:
    1. Read Redis. If Hit -> Evaluate & Return.
    2. On Miss -> Read PostgreSQL.
    3. Update Redis cache accordingly & Return.
    """
    # -------------------------------------------------------------
    # Step 1: Redis Cache Lookup
    # -------------------------------------------------------------
    cached_entry = get_cached_url_data(short_code)

    if cached_entry is not None:
        # Negative Cache Hit: code confirmed non-existent
        if cached_entry.get("not_found"):
            raise LinkNotFoundException()

        # Positive Cache Hit: evaluate state using cached timestamps
        is_active = cached_entry["is_active"]
        expires_at_str = cached_entry.get("expires_at")
        expires_at = parse_datetime(expires_at_str) if expires_at_str else None

        _check_link_state(is_active=is_active, expires_at=expires_at)
        return cached_entry["original_url"]

    # -------------------------------------------------------------
    # Step 2: Database Fallback (Cache Miss or Redis Unavailable)
    # -------------------------------------------------------------
    try:
        link = (
            ShortURL.objects.only("original_url", "is_active", "expires_at")
            .get(short_code=short_code)
        )
    except ShortURL.DoesNotExist:
        # Prevent cache penetration: store sentinel in Redis
        cache_not_found(short_code)
        raise LinkNotFoundException()

    # -------------------------------------------------------------
    # Step 3: Populate Cache & Verify State
    # -------------------------------------------------------------
    # Verify state before returning
    _check_link_state(is_active=link.is_active, expires_at=link.expires_at)

    # Populate cache for subsequent requests
    cache_url(
        short_code=link.short_code,
        original_url=link.original_url,
        is_active=link.is_active,
        expires_at=link.expires_at,
    )

    return link.original_url