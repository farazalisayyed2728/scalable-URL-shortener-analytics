import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.links.models import ShortURL

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestURLAPILifecycle:
    def setup_method(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="user1@example.com", password="Password123!"
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com", password="Password123!"
        )

    def test_anonymous_url_creation_happy_path(self):
        """Verify unauthenticated user can shorten a URL."""
        response = self.client.post(
            "/api/urls/",
            {"original_url": "https://www.djangoproject.com/foundation/"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["short_code"]) == 7
        assert data["original_url"] == "https://www.djangoproject.com/foundation/"
        assert data["is_custom"] is False
        assert "X-RateLimit-Limit" in response.headers

    def test_authenticated_custom_url_creation(self):
        """Verify authenticated user can allocate custom short codes."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            "/api/urls/",
            {
                "original_url": "https://fastapi.tiangolo.com",
                "custom_code": "fastapi_docs",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["short_code"] == "fastapi_docs"
        assert data["is_custom"] is True

        # Confirm ownership in database
        link = ShortURL.objects.get(short_code="fastapi_docs")
        assert link.owner == self.user1

    def test_duplicate_custom_code_returns_409(self):
        """Verify custom code collisions return 409 Conflict with proper envelope."""
        self.client.force_authenticate(user=self.user1)
        self.client.post(
            "/api/urls/",
            {"original_url": "https://google.com", "custom_code": "unique_code"},
            format="json",
        )

        # Attempt to create the same custom code with user 2
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            "/api/urls/",
            {"original_url": "https://bing.com", "custom_code": "unique_code"},
            format="json",
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error"]["code"] == "CODE_ALREADY_TAKEN"

    def test_maximum_length_url_boundary(self):
        """Verify URLs up to 2048 characters are accepted and > 2048 are rejected."""
        base = "https://example.com/search?q="
        valid_long_url = base + ("a" * (2048 - len(base)))
        invalid_long_url = base + ("a" * (2049 - len(base)))

        # 2048 chars should succeed
        res_valid = self.client.post(
            "/api/urls/", {"original_url": valid_long_url}, format="json"
        )
        assert res_valid.status_code == status.HTTP_201_CREATED

        # 2049 chars should fail with 400 Bad Request
        res_invalid = self.client.post(
            "/api/urls/", {"original_url": invalid_long_url}, format="json"
        )
        assert res_invalid.status_code == status.HTTP_400_BAD_REQUEST

    def test_cross_user_resource_protection_returns_404(self):
        """Verify User 2 cannot access or mutate User 1's link (returns 404 to prevent existence leak)."""
        link = ShortURL.objects.create(
            short_code="user1_link",
            original_url="https://secret.corp",
            owner=self.user1,
        )

        # User 2 tries to GET User 1's link detail
        self.client.force_authenticate(user=self.user2)
        get_res = self.client.get(f"/api/urls/{link.short_code}/")
        assert get_res.status_code == status.HTTP_404_NOT_FOUND
        assert get_res.json()["error"]["code"] == "LINK_NOT_FOUND"

        # User 2 tries to PATCH User 1's link
        patch_res = self.client.patch(
            f"/api/urls/{link.short_code}/",
            {"original_url": "https://hacked.com"},
            format="json",
        )
        assert patch_res.status_code == status.HTTP_404_NOT_FOUND

        # User 2 tries to DELETE User 1's link
        del_res = self.client.delete(f"/api/urls/{link.short_code}/")
        assert del_res.status_code == status.HTTP_404_NOT_FOUND

    def test_soft_delete_and_redirect_semantics(self):
        """Verify DELETE marks link inactive and subsequent redirect returns 410 Gone."""
        self.client.force_authenticate(user=self.user1)
        link = ShortURL.objects.create(
            short_code="deleteme",
            original_url="https://temporary.org",
            owner=self.user1,
        )

        # 1. Successful delete
        del_res = self.client.delete(f"/api/urls/{link.short_code}/")
        assert del_res.status_code == status.HTTP_204_NO_CONTENT

        link.refresh_from_db()
        assert link.is_active is False

        # 2. Redirect to soft-deleted link returns 410 Gone
        redirect_res = self.client.get(f"/{link.short_code}")
        assert redirect_res.status_code == status.HTTP_410_GONE
        assert redirect_res.json()["error"]["code"] == "LINK_EXPIRED"
        