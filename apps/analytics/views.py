from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import Click
from apps.analytics.serializers import (
    ClickLogSerializer,
    URLAnalyticsResponseSerializer,
    UserOverviewAnalyticsResponseSerializer,
)
from apps.analytics.services.aggregation import (
    get_url_analytics_summary,
    get_user_overview_analytics,
)
from apps.core.exceptions import LinkNotFoundException
from apps.core.pagination import StandardCursorPagination
from apps.core.serializers import ErrorEnvelopeSerializer
from apps.links.models import ShortURL


class URLAnalyticsAPIView(APIView):
    """
    Endpoint: GET /api/urls/<short_code>/analytics/?days=30
    Owner-scoped dashboard metrics for a short URL.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get URL analytics dashboard",
        description="Returns aggregated metrics for a short link: total clicks, today's clicks, top referrers, device breakdown, and daily time-series.",
        parameters=[
            OpenApiParameter("days", OpenApiTypes.INT, description="Time window in days (1 to 90, default 30)", required=False)
        ],
        responses={
            status.HTTP_200_OK: URLAnalyticsResponseSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
            status.HTTP_404_NOT_FOUND: ErrorEnvelopeSerializer,
        },
        tags=["Analytics"],
    )
    def get(self, request: Request, short_code: str) -> Response:
        try:
            link = ShortURL.objects.get(short_code=short_code, owner=request.user)
        except ShortURL.DoesNotExist:
            raise LinkNotFoundException()

        days_param = request.query_params.get("days", "30")
        try:
            days = min(max(int(days_param), 1), 90)
        except ValueError:
            days = 30

        summary = get_url_analytics_summary(link, days=days)
        serializer = URLAnalyticsResponseSerializer(summary)
        return Response(serializer.data, status=status.HTTP_200_OK)


class URLClickLogAPIView(APIView):
    """
    Endpoint: GET /api/urls/<short_code>/clicks/
    Cursor-paginated click stream for a short link.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination

    @extend_schema(
        summary="Stream raw click logs",
        description="Returns cursor-paginated raw click events for a short link. Uses constant-time keyset pagination.",
        parameters=[
            OpenApiParameter("cursor", OpenApiTypes.STR, description="Pagination cursor pointer", required=False),
            OpenApiParameter("page_size", OpenApiTypes.INT, description="Number of results per page (max 100)", required=False),
        ],
        responses={
            status.HTTP_200_OK: ClickLogSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
            status.HTTP_404_NOT_FOUND: ErrorEnvelopeSerializer,
        },
        tags=["Analytics"],
    )
    def get(self, request: Request, short_code: str) -> Response:
        try:
            ShortURL.objects.get(short_code=short_code, owner=request.user)
        except ShortURL.DoesNotExist:
            raise LinkNotFoundException()

        queryset = Click.objects.filter(short_code=short_code).order_by("-clicked_at")
        paginator = self.pagination_class()
        paged_queryset = paginator.paginate_queryset(queryset, request, view=self)

        serializer = ClickLogSerializer(paged_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class UserAnalyticsOverviewAPIView(APIView):
    """
    Endpoint: GET /api/analytics/overview/
    Aggregated metrics across all short URLs owned by the user.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="User analytics overview",
        description="Returns combined aggregated metrics for all short URLs owned by the authenticated user.",
        responses={
            status.HTTP_200_OK: UserOverviewAnalyticsResponseSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
        },
        tags=["Analytics"],
    )
    def get(self, request: Request) -> Response:
        summary = get_user_overview_analytics(request.user)
        serializer = UserOverviewAnalyticsResponseSerializer(summary)
        return Response(serializer.data, status=status.HTTP_200_OK)