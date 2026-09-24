from django.utils import timezone

from apps.core.exceptions import (
    LinkExpiredException,
    LinkNotFoundException,
)
from apps.links.models import ShortURL


def resolve_short_code(short_code: str) -> str:
    """
    Resolve a short code to its original URL.

    Raises:
        LinkNotFoundException: short code does not exist.
        LinkExpiredException: link is inactive or expired.
    """

    try:
        link = (
            ShortURL.objects
            .only("original_url", "is_active", "expires_at")
            .get(short_code=short_code)
        )
    except ShortURL.DoesNotExist:
        raise LinkNotFoundException()

    # Link has been manually disabled
    if not link.is_active:
        raise LinkExpiredException(
            message="This short link has been disabled."
        )

    # Link has expired
    if link.expires_at is not None and timezone.now() >= link.expires_at:
        raise LinkExpiredException(
            message="This short link has expired."
        )

    return link.original_url