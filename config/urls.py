from django.contrib import admin
from django.urls import include, path, re_path
from apps.links.views import RedirectShortURLView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.links.urls")),

re_path(
    r"^(?P<short_code>[A-Za-z0-9_-]{3,32})/?$",
    RedirectShortURLView.as_view(),
    name="short-url-redirect",
    ),
]
