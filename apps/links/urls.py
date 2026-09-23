from django.urls import path
from .views import ShortURLCreateAPIView

urlpatterns = [
    path("urls/", ShortURLCreateAPIView.as_view(), name="url-create"),
]