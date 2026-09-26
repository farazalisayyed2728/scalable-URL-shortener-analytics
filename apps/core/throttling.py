from typing import Optional

from django.conf import settings
from rest_framework.request import Request
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from .ratelimit import check_rate_limit, get_client_ip


class CreateURLRateThrottle(BaseThrottle):
    """
    Applies per-IP rate limiting to URL creation requests using Redis.
    """

    def __init__(self):
        self.remaining: int = 0
        self.reset_seconds: int = 0
        self.limit: int = settings.RATE_LIMIT_CREATE_PER_MIN

    def allow_request(self, request: Request, view: APIView) -> bool:
        ip_address = get_client_ip(request)

        is_allowed, remaining, reset_seconds = check_rate_limit(
            key_identifier=ip_address,
            action="create_url",
            limit=self.limit,
            window_seconds=60,
        )

        self.remaining = remaining
        self.reset_seconds = reset_seconds

        # Store on request object so the view can populate X-RateLimit headers
        request.rate_limit_limit = self.limit
        request.rate_limit_remaining = self.remaining
        request.rate_limit_reset = self.reset_seconds

        return is_allowed

    def wait(self) -> Optional[int]:
        """
        Returns the duration in seconds to wait before retrying (for Retry-After).
        """
        return self.reset_seconds