import pytest
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, Throttled, ValidationError
from rest_framework.test import APIRequestFactory

from apps.core.exceptions import (
    CodeAlreadyTakenException,
    LinkExpiredException,
    LinkNotFoundException,
    custom_exception_handler,
)


class TestUnifiedErrorHandling:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/api/test/")
        self.context = {"request": self.request}

    def test_validation_error_envelope_400(self):
        """Verify 400 Bad Request maps to VALIDATION_ERROR with field details."""
        exc = ValidationError({"original_url": ["Enter a valid URL."]})
        response = custom_exception_handler(exc, self.context)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in data["error"]
        assert "original_url" in data["error"]["details"]

    def test_authentication_error_envelope_401(self):
        """Verify 401 Unauthorized maps to AUTHENTICATION_REQUIRED."""
        exc = AuthenticationFailed("Token is invalid or expired.")
        response = custom_exception_handler(exc, self.context)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"]["code"] == "AUTHENTICATION_REQUIRED"
        assert response.data["error"]["message"] == "Token is invalid or expired."
        assert response.data["error"]["details"] is None

    def test_permission_denied_envelope_403(self):
        """Verify 403 Forbidden maps to PERMISSION_DENIED."""
        exc = PermissionDenied("You do not own this resource.")
        response = custom_exception_handler(exc, self.context)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error"]["code"] == "PERMISSION_DENIED"

    def test_not_found_envelope_404(self):
        """Verify 404 Not Found maps to LINK_NOT_FOUND or NOT_FOUND."""
        exc = LinkNotFoundException()
        response = custom_exception_handler(exc, self.context)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"]["code"] == "LINK_NOT_FOUND"

    def test_conflict_envelope_409(self):
        """Verify 409 Conflict maps to CODE_ALREADY_TAKEN."""
        exc = CodeAlreadyTakenException()
        response = custom_exception_handler(exc, self.context)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"]["code"] == "CODE_ALREADY_TAKEN"

    def test_link_expired_envelope_410(self):
        """Verify 410 Gone maps to LINK_EXPIRED."""
        exc = LinkExpiredException()
        response = custom_exception_handler(exc, self.context)

        assert response.status_code == status.HTTP_410_GONE
        assert response.data["error"]["code"] == "LINK_EXPIRED"

    def test_rate_limited_envelope_429(self):
        """Verify 429 Too Many Requests maps to RATE_LIMITED with retry seconds."""
        exc = Throttled(wait=45)
        response = custom_exception_handler(exc, self.context)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.data["error"]["code"] == "RATE_LIMITED"
        assert "45 seconds" in response.data["error"]["message"]

    def test_unhandled_crash_envelope_500(self):
        """Verify unhandled Python exceptions map to sanitized INTERNAL_SERVER_ERROR."""
        exc = RuntimeError("Fatal database connection crash with raw credentials inside!")
        response = custom_exception_handler(exc, self.context)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        # Invariant: Must NOT leak internal RuntimeError message to user
        assert "credentials" not in response.data["error"]["message"]
        assert response.data["error"]["details"] is None