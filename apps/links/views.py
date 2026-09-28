from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponseRedirect, JsonResponse


from django.http import HttpResponseRedirect
from django.views import View

from apps.core.exceptions import (
    LinkNotFoundException,
    LinkExpiredException,
)

from apps.core.exceptions import LinkNotFoundException
from apps.links.models import ShortURL
from .serializers import (
    ShortURLCreateRequestSerializer,
    ShortURLResponseSerializer,
    ShortURLUpdateSerializer,
)
from .services.updater import soft_delete_short_url, update_short_url

from apps.core.throttling import CreateURLRateThrottle 
from .services.resolver import resolve_short_code

from .serializers import (
    ShortURLCreateRequestSerializer,
    ShortURLResponseSerializer,
)
from .services.shortener import create_short_url


class ShortURLCreateAPIView(APIView):
    """
    Endpoint: POST /api/urls/
    Creates a new short URL. Throttled to 100 requests/minute/IP.
    """
    permission_classes = [AllowAny]
    throttle_classes = [CreateURLRateThrottle]  # Attach Rate Limiter

    def post(self, request: Request) -> Response:
        serializer = ShortURLCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        owner = request.user if request.user.is_authenticated else None

        short_url_instance = create_short_url(
            original_url=validated_data["original_url"],
            owner=owner,
            custom_code=validated_data.get("custom_code"),
            expires_at=validated_data.get("expires_at"),
        )

        response_serializer = ShortURLResponseSerializer(short_url_instance)
        response = Response(response_serializer.data, status=status.HTTP_201_CREATED)

        # Inject rate limit telemetry headers into the response
        if hasattr(request, "rate_limit_limit"):
            response["X-RateLimit-Limit"] = str(request.rate_limit_limit)
            response["X-RateLimit-Remaining"] = str(request.rate_limit_remaining)
            response["X-RateLimit-Reset"] = str(request.rate_limit_reset)

        return response


class RedirectShortURLView(View):

    def get(self, request, short_code: str, *args, **kwargs):

        try:
            destination_url = resolve_short_code(short_code)

        except LinkNotFoundException as exc:
            return JsonResponse(
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details if exc.details else None,
                    }
                },
                status=exc.http_status,
            )

        except LinkExpiredException as exc:
            return JsonResponse(
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details if exc.details else None,
                    }
                },
                status=exc.http_status,
            )

        response = HttpResponseRedirect(
            redirect_to=destination_url
        )

        response["Cache-Control"] = (
            "no-store, no-cache, private, "
            "must-revalidate, max-age=0"
        )

        response["Pragma"] = "no-cache"

        return response

from .services.updater import soft_delete_short_url, update_short_url

# In apps/links/views.py:

from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
# (Replace AllowAny or adjust permissions on detail view)

class ShortURLDetailUpdateDeleteAPIView(APIView):
    """
    Endpoint: /api/urls/<short_code>/
    Enforces object-level resource ownership. Non-owners receive 404 Not Found.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, short_code: str) -> Response:
        try:
            # Security: Scope query strictly to request.user
            link = ShortURL.objects.get(short_code=short_code, owner=request.user)
        except ShortURL.DoesNotExist:
            raise LinkNotFoundException()  # Returns 404, preventing existence leak

        serializer = ShortURLResponseSerializer(link)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request: Request, short_code: str) -> Response:
        try:
            link = ShortURL.objects.get(short_code=short_code, owner=request.user)
        except ShortURL.DoesNotExist:
            raise LinkNotFoundException()

        serializer = ShortURLUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_link = update_short_url(
            short_code=link.short_code,
            **serializer.validated_data,
        )

        response_serializer = ShortURLResponseSerializer(updated_link)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request: Request, short_code: str) -> Response:
        try:
            link = ShortURL.objects.get(short_code=short_code, owner=request.user)
        except ShortURL.DoesNotExist:
            raise LinkNotFoundException()

        soft_delete_short_url(link.short_code)
        return Response(status=status.HTTP_204_NO_CONTENT)

# In apps/links/views.py:

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPageNumberPagination
from apps.core.throttling import CreateURLRateThrottle
from apps.links.models import ShortURL
from .serializers import (
    ShortURLCreateRequestSerializer,
    ShortURLResponseSerializer,
    ShortURLUpdateSerializer,
)
from .services.shortener import create_short_url
from .services.updater import soft_delete_short_url, update_short_url


class ShortURLListCreateAPIView(APIView):
    """
    Endpoint: /api/urls/
    - POST: Create a short URL (Rate limited, open to all).
    - GET: List authenticated user's URLs (Paginated, owner-scoped).
    """
    pagination_class = StandardPageNumberPagination

    def get_permissions(self):
        # POST is open (or handles optional user); GET requires authentication
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_throttles(self):
        # Apply rate limiting throttle strictly to POST creation
        if self.request.method == "POST":
            return [CreateURLRateThrottle()]
        return []

    def get(self, request: Request) -> Response:
        # 1. Fetch only URLs owned by the authenticated user
        # Uses idx_shorturl_owner_created composite index directly!
        queryset = ShortURL.objects.filter(owner=request.user).order_by("-created_at")

        # 2. Paginate queryset
        paginator = self.pagination_class()
        paged_queryset = paginator.paginate_queryset(queryset, request, view=self)

        # 3. Serialize and return standardized envelope
        serializer = ShortURLResponseSerializer(paged_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = ShortURLCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        owner = request.user if request.user.is_authenticated else None

        short_url_instance = create_short_url(
            original_url=validated_data["original_url"],
            owner=owner,
            custom_code=validated_data.get("custom_code"),
            expires_at=validated_data.get("expires_at"),
        )

        response_serializer = ShortURLResponseSerializer(short_url_instance)
        response = Response(response_serializer.data, status=status.HTTP_201_CREATED)

        if hasattr(request, "rate_limit_limit"):
            response["X-RateLimit-Limit"] = str(request.rate_limit_limit)
            response["X-RateLimit-Remaining"] = str(request.rate_limit_remaining)
            response["X-RateLimit-Reset"] = str(request.rate_limit_reset)

        return response