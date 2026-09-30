from django.urls import path
from .views import (
    URLAnalyticsAPIView,
    URLClickLogAPIView,
    UserAnalyticsOverviewAPIView,
)

urlpatterns = [
    path("analytics/overview/", UserAnalyticsOverviewAPIView.as_view(), name="analytics-overview"),
    path("urls/<str:short_code>/analytics/", URLAnalyticsAPIView.as_view(), name="url-analytics"),
    path("urls/<str:short_code>/clicks/", URLClickLogAPIView.as_view(), name="url-clicks"),
]