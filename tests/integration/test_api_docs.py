import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestOpenAPIDocumentation:

    def test_openapi_schema_endpoint_generates_valid_spec(self):
        """Verify GET /api/schema/ returns 200 OK and valid OpenAPI 3.0 YAML."""
        client = APIClient()
        response = client.get("/api/schema/")
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")
        assert "openapi: 3.0.3" in content
        assert "ShortLink Scalable Backend API" in content
        assert "/api/urls/" in content
        assert "/api/auth/login/" in content

    def test_swagger_ui_endpoint_returns_200(self):
        """Verify GET /api/docs/ returns 200 OK and serves Swagger UI HTML."""
        client = APIClient()
        response = client.get("/api/docs/")
        assert response.status_code == status.HTTP_200_OK
        assert "swagger-ui" in response.content.decode("utf-8")

    def test_redoc_endpoint_returns_200(self):
        """Verify GET /api/redoc/ returns 200 OK and serves Redoc HTML."""
        client = APIClient()
        response = client.get("/api/redoc/")
        assert response.status_code == status.HTTP_200_OK
        assert "redoc" in response.content.decode("utf-8")