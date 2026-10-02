from django.urls import path

from .views import (
    UserRegisterAPIView,
    UserTokenObtainPairAPIView,
    UserTokenRefreshAPIView,
)

urlpatterns = [
    path(
        "register/",
        UserRegisterAPIView.as_view(),
        name="register",
    ),
    path(
        "login/",
        UserTokenObtainPairAPIView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "refresh/",
        UserTokenRefreshAPIView.as_view(),
        name="token_refresh",
    ),
]