from django.urls import path
from .views import ShortURLCreateAPIView

from .views import (
    ShortURLCreateAPIView,
    ShortURLDetailUpdateDeleteAPIView,
)

urlpatterns = [
    path("urls/", ShortURLCreateAPIView.as_view(), name="url-create"),
    path("urls/<str:short_code>/", ShortURLDetailUpdateDeleteAPIView.as_view(), name="url-detail-update-delete"),
]
