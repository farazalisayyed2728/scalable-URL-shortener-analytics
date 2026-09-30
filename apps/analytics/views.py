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
from apps.links.models import ShortURL


class URLAnalyticsAPIView(APIView):
    """
    Endpoint: GET /api/urls/<short_code>/analytics/?days=30
    Provides aggregated dashboard metrics for a specific short link. Owner-scoped.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, short_code: str) -> Response:
        try:
            link = ShortURL.objects.get(short_code=short_code, owner=request.user)
        except ShortURL.DoesNotExist:
            raise LinkNotFoundException()

        days_param = request.query_params.get("days", "30")
        try:
            days = min(max(int(days_param), 1), 90)  # Bound between 1 and 90 days
        except ValueError:
            days = 30

        summary = get_url_analytics_summary(link, days=days)
        serializer = URLAnalyticsResponseSerializer(summary)
        return Response(serializer.data, status=status.HTTP_200_OK)


class URLClickLogAPIView(APIView):
    """
    Endpoint: GET /api/urls/<short_code>/clicks/
    Returns cursor-paginated raw click event stream. Owner-scoped.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination

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
    Provides cross-link aggregated overview for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        summary = get_user_overview_analytics(request.user)
        serializer = UserOverviewAnalyticsResponseSerializer(summary)
        return Response(serializer.data, status=status.HTTP_200_OK)