from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.health import check_database, check_redis, get_system_health


class LivenessProbeAPIView(APIView):
    """
    Kubernetes / Container Liveness Probe.
    Checks strictly if the web server process is responsive.
    Does NOT query external dependencies to avoid thundering-herd restart loops.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Process Liveness Probe",
        description="Returns 200 OK if the Python application process is alive and responsive.",
        responses={status.HTTP_200_OK: dict},
        tags=["Health & Probes"],
    )
    def get(self, request: Request) -> Response:
        return Response({"status": "alive"}, status=status.HTTP_200_OK)


class ReadinessProbeAPIView(APIView):
    """
    Kubernetes / Load Balancer Readiness Probe.
    Verifies that downstream dependencies (PostgreSQL, Redis) are reachable.
    Returns 200 OK to accept traffic, or 503 Service Unavailable to temporarily pull out of the load balancer.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Dependency Readiness Probe",
        description="Verifies downstream database and cache reachability. Returns 503 if dependencies fail.",
        responses={
            status.HTTP_200_OK: dict,
            status.HTTP_503_SERVICE_UNAVAILABLE: dict,
        },
        tags=["Health & Probes"],
    )
    def get(self, request: Request) -> Response:
        is_healthy, payload = get_system_health()
        http_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=http_status)


class HealthCheckAPIView(APIView):
    """
    Aggregated operational health check endpoint for monitoring tools and external dashboards.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="System Health Check",
        description="Comprehensive system health status report including dependency latencies.",
        responses={
            status.HTTP_200_OK: dict,
            status.HTTP_503_SERVICE_UNAVAILABLE: dict,
        },
        tags=["Health & Probes"],
    )
    def get(self, request: Request) -> Response:
        is_healthy, payload = get_system_health()
        http_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=http_status)