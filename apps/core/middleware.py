import logging
import time
import uuid
from typing import Callable
from django.http import HttpRequest, HttpResponse

from apps.core.logging import request_id_ctx
from apps.core.ratelimit import get_client_ip

logger = logging.getLogger("access")


class RequestIDMiddleware:
    """
    Middleware that manages the X-Request-ID lifecycle:
    1. Reads incoming X-Request-ID header or generates a fresh UUID4.
    2. Stores request_id in contextvars for downstream loggers.
    3. Attaches X-Request-ID header to the outgoing HTTP response.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Extract from client/ingress or generate fresh UUID4
        incoming_id = request.headers.get("X-Request-ID")
        req_id = incoming_id.strip() if incoming_id else str(uuid.uuid4())

        # Bind to request object and contextvars storage
        request.request_id = req_id
        token = request_id_ctx.set(req_id)

        try:
            response = self.get_response(request)
        finally:
            # Clean up contextvar token to prevent leakage in pooled threads
            request_id_ctx.reset(token)

        # Attach to outgoing response header
        response["X-Request-ID"] = req_id
        return response


class AccessLogMiddleware:
    """
    Middleware that records structured access metrics for completed HTTP requests:
    method, path, status, latency_ms, client_ip, and request_id.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip noisy static / internal polling routes if needed
        start_time = time.perf_counter()

        response = self.get_response(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        client_ip = get_client_ip(request)

        # Log completed request with structured metrics
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "latency_ms": round(duration_ms, 2),
                "client_ip": client_ip,
            },
        )

        return response