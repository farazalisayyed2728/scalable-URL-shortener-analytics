from datetime import datetime
from typing import Optional

from django.db import transaction

from apps.core.exceptions import LinkNotFoundException
from apps.links.models import ShortURL
from .cache import delete_cached_url
from .validators import validate_original_url


def update_short_url(
    short_code: str,
    *,
    original_url: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    is_active: Optional[bool] = None,
) -> ShortURL:
    """
    Updates mutable fields of a ShortURL and purges its Redis cache.
    """
    try:
        link = ShortURL.objects.get(short_code=short_code)
    except ShortURL.DoesNotExist:
        raise LinkNotFoundException()

    update_fields = ["updated_at"]

    if original_url is not None:
        link.original_url = validate_original_url(original_url)
        update_fields.append("original_url")

    if expires_at is not None:
        link.expires_at = expires_at
        update_fields.append("expires_at")

    if is_active is not None:
        link.is_active = is_active
        update_fields.append("is_active")

    # 1. Commit changes to PostgreSQL
    with transaction.atomic():
        link.save(update_fields=update_fields)

    # 2. Invalidate cache AFTER DB commit
    # If the DB commit fails, this line is never reached.
    delete_cached_url(short_code)

    return link


def soft_delete_short_url(short_code: str) -> None:
    """
    Soft-deletes a ShortURL by setting is_active=False and purging Redis cache.
    Subsequent redirects will return HTTP 410 Gone.
    """
    update_short_url(short_code, is_active=False)