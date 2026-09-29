import logging
import uuid

from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.tasks import record_click_event
from apps.core.exceptions import LinkNotFoundException
from apps.core.pagination import StandardPageNumberPagination
from apps.core.ratelimit import get_client_ip
from apps.core.throttling import CreateURLRateThrottle
from apps.links.models import ShortURL

from .serializers import (
    ShortURLCreateRequestSerializer,
    ShortURLResponseSerializer,
    ShortURLUpdateSerializer,
)
from .services.resolver import resolve_short_code
from .services.shortener import create_short_url
from .services.updater import soft_delete_short_url, update_short_url


logger = logging.getLogger(__name__)


class ShortURLListCreateAPIView(APIView):
    """
    Endpoint: /api/urls/

    POST:
        Create a short URL.
        Open to authenticated and anonymous users.
        Rate limited.

    GET:
        List authenticated user's URLs.
        Paginated and owner-scoped.
    """

    pagination_class = StandardPageNumberPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]

        return [IsAuthenticated()]

    def get_throttles(self):
        if self.request.method == "POST":
            return [CreateURLRateThrottle()]

        return []

    def get(self, request: Request) -> Response:
        queryset = (
            ShortURL.objects
            .filter(owner=request.user)
            .order_by("-created_at")
        )

        paginator = self.pagination_class()

        paged_queryset = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        serializer = ShortURLResponseSerializer(
            paged_queryset,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = ShortURLCreateRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        owner = (
            request.user
            if request.user.is_authenticated
            else None
        )

        short_url_instance = create_short_url(
            original_url=validated_data["original_url"],
            owner=owner,
            custom_code=validated_data.get("custom_code"),
            expires_at=validated_data.get("expires_at"),
        )

        response_serializer = ShortURLResponseSerializer(
            short_url_instance
        )

        response = Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

        if hasattr(request, "rate_limit_limit"):
            response["X-RateLimit-Limit"] = str(
                request.rate_limit_limit
            )
            response["X-RateLimit-Remaining"] = str(
                request.rate_limit_remaining
            )
            response["X-RateLimit-Reset"] = str(
                request.rate_limit_reset
            )

        return response


class ShortURLDetailUpdateDeleteAPIView(APIView):
    """
    Endpoint: /api/urls/<short_code>/

    All operations are restricted to the authenticated owner.
    Non-owners receive 404 to prevent resource existence leaks.
    """

    permission_classes = [IsAuthenticated]

    def _get_owned_link(
        self,
        request: Request,
        short_code: str,
    ) -> ShortURL:
        try:
            return ShortURL.objects.get(
                short_code=short_code,
                owner=request.user,
            )
        except ShortURL.DoesNotExist:
            raise LinkNotFoundException()

    def get(
        self,
        request: Request,
        short_code: str,
    ) -> Response:
        link = self._get_owned_link(
            request,
            short_code,
        )

        serializer = ShortURLResponseSerializer(link)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(
        self,
        request: Request,
        short_code: str,
    ) -> Response:
        link = self._get_owned_link(
            request,
            short_code,
        )

        serializer = ShortURLUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        updated_link = update_short_url(
            short_code=link.short_code,
            **serializer.validated_data,
        )

        response_serializer = ShortURLResponseSerializer(
            updated_link
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    def delete(
        self,
        request: Request,
        short_code: str,
    ) -> Response:
        link = self._get_owned_link(
            request,
            short_code,
        )

        soft_delete_short_url(link.short_code)

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class RedirectShortURLView(APIView):
    """
    Endpoint: GET /<short_code>

    Resolves the short URL, asynchronously records complete
    click telemetry through Celery, and immediately returns
    an HTTP 302 redirect.

    Telemetry or broker failures never break the redirect.
    """

    permission_classes = [AllowAny]

    def get(
        self,
        request,
        short_code: str,
        *args,
        **kwargs,
    ):
        # Resolve destination URL.
        destination_url = resolve_short_code(short_code)

        # Generate idempotent event ID at ingress.
        event_id = str(uuid.uuid4())

        # Extract click telemetry.
        client_ip = get_client_ip(request)
        user_agent = request.META.get(
            "HTTP_USER_AGENT",
            "",
        )
        referrer = request.META.get(
            "HTTP_REFERER"
        )
        clicked_at_str = timezone.now().isoformat()

        # Optional telemetry fields.
        # These can be populated by middleware / geo / UA parsing
        # before dispatching the task if available.
        country_code = getattr(
            request,
            "country_code",
            None,
        )

        device_type = getattr(
            request,
            "device_type",
            None,
        )

        browser = getattr(
            request,
            "browser",
            None,
        )

        os = getattr(
            request,
            "os",
            None,
        )

        is_bot = getattr(
            request,
            "is_bot",
            False,
        )

        # Enqueue telemetry asynchronously.
        try:
            record_click_event.delay(
                short_code=short_code,
                event_id=event_id,
                clicked_at_str=clicked_at_str,
                ip_address=client_ip,
                user_agent=user_agent,
                referrer=referrer,
                country_code=country_code,
                device_type=device_type,
                browser=browser,
                os=os,
                is_bot=is_bot,
            )

        except Exception as exc:
            # Never allow telemetry/broker failure to break redirects.
            logger.warning(
                "telemetry_enqueue_failed",
                extra={
                    "short_code": short_code,
                    "event_id": event_id,
                    "error": str(exc),
                },
            )

        # Immediate HTTP 302 redirect.
        response = HttpResponseRedirect(
            redirect_to=destination_url
        )

        response["Cache-Control"] = (
            "no-store, no-cache, private, "
            "must-revalidate, max-age=0"
        )
        response["Pragma"] = "no-cache"

        return response