from unittest.mock import patch
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestHealthChecksAndProbes:
    def setup_method(self):
        self.client = APIClient()

    def test_liveness_probe_returns_200_alive(self):
        """Verify liveness probe returns 200 without checking external dependencies."""
        response = self.client.get("/health/liveness/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "alive"}

    def test_readiness_probe_healthy_state(self):
        """Verify readiness probe returns 200 when database and redis are responsive."""
        response = self.client.get("/health/readiness/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["dependencies"]["database"]["status"] == "healthy"
        assert data["dependencies"]["redis"]["status"] == "healthy"

    def test_readiness_probe_database_failure_returns_503(self):
        """Verify readiness probe returns 503 when the database fails."""
        with patch("apps.core.health.check_database", return_value=(False, 50.0, "DB Down")):
            response = self.client.get("/health/readiness/")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["dependencies"]["database"]["status"] == "unhealthy"
            assert data["dependencies"]["database"]["detail"] == "DB Down"

    def test_readiness_probe_redis_failure_returns_503(self):
        """Verify readiness probe returns 503 when Redis fails."""
        with patch("apps.core.health.check_redis", return_value=(False, 100.0, "Redis Connection Refused")):
            response = self.client.get("/health/readiness/")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["dependencies"]["redis"]["status"] == "unhealthy"

    def test_health_check_endpoint_aggregates_latencies(self):
        """Verify /health/ includes measured latency_ms for both dependencies."""
        response = self.client.get("/health/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "latency_ms" in data["dependencies"]["database"]
        assert "latency_ms" in data["dependencies"]["redis"]
        assert isinstance(data["dependencies"]["database"]["latency_ms"], float)