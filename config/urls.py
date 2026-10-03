from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.links.views import RedirectShortURLView

from apps.core.views import (
    HealthCheckAPIView,
    LivenessProbeAPIView,
    ReadinessProbeAPIView,
)
from apps.links.views import RedirectShortURLView

urlpatterns = [
    path("admin/", admin.site.urls),

    # REST APIs
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.analytics.urls")),
    path("api/", include("apps.links.urls")),

    # Infrastructure Health & Lifecycle Probes (No Auth Required)
    path("health/", HealthCheckAPIView.as_view(), name="health-check"),
    path("health/liveness/", LivenessProbeAPIView.as_view(), name="health-liveness"),
    path("health/readiness/", ReadinessProbeAPIView.as_view(), name="health-readiness"),

    # OpenAPI Schema and Interactive Documentation Views
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    re_path(
        r"^(?P<short_code>[A-Za-z0-9_-]{3,32})/?$",
        RedirectShortURLView.as_view(),
        name="short-url-redirect",
    ),
]
