import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.mark.django_db
def test_refresh_token_for_deleted_user_returns_unauthorized():
    user = User.objects.create_user(
        email="deleted-user@example.com",
        password="Test-Password-2026!",
    )
    refresh_token = str(RefreshToken.for_user(user))
    user.delete()

    response = APIClient().post(
        "/api/auth/refresh/",
        {"refresh": refresh_token},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_valid_refresh_token_returns_new_access_token():
    user = User.objects.create_user(
        email="refresh-user@example.com",
        password="Test-Password-2026!",
    )
    refresh_token = str(RefreshToken.for_user(user))

    response = APIClient().post(
        "/api/auth/refresh/",
        {"refresh": refresh_token},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["access"]
