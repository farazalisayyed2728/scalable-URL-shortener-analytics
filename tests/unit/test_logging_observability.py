import json
import logging
from django.test import RequestFactory
from apps.core.logging import JSONLogFormatter, RequestIDFilter, request_id_ctx
from apps.core.middleware import RequestIDMiddleware


class TestLoggingAndObservability:

    def test_request_id_middleware_generates_and_attaches_header(self):
        """Verify middleware generates a UUID4 when no header is supplied."""
        factory = RequestFactory()
        request = factory.get("/api/urls/")

        middleware = RequestIDMiddleware(lambda req: req)
        # Mock a minimal HttpResponse
        from django.http import HttpResponse
        middleware.get_response = lambda req: HttpResponse("OK")

        response = middleware(request)

        assert "X-Request-ID" in response
        assert len(response["X-Request-ID"]) >= 32
        assert hasattr(request, "request_id")
        assert response["X-Request-ID"] == request.request_id

    def test_request_id_middleware_preserves_incoming_header(self):
        """Verify middleware propagates an existing client-supplied X-Request-ID."""
        custom_id = "external-client-trace-999"
        factory = RequestFactory()
        request = factory.get("/api/urls/", HTTP_X_REQUEST_ID=custom_id)

        from django.http import HttpResponse
        middleware = RequestIDMiddleware(lambda req: HttpResponse("OK"))

        response = middleware(request)

        assert response["X-Request-ID"] == custom_id
        assert request.request_id == custom_id

    def test_json_formatter_serializes_structured_metadata_and_redacts(self):
        """Verify JSONLogFormatter outputs valid JSON, includes request_id, and masks secrets."""
        token = request_id_ctx.set("trace-uuid-42")
        try:
            logger = logging.getLogger("test_logger")
            record = logger.makeRecord(
                name="test_logger",
                level=logging.INFO,
                fn="test.py",
                lno=10,
                msg="User login attempted",
                args=(),
                exc_info=None,
                extra={"user_id": 42, "password": "SuperSecretPassword123!", "token": "jwt-token-val"},
            )

            # Apply request_id filter and JSON format
            RequestIDFilter().filter(record)
            formatter = JSONLogFormatter()
            formatted_json_str = formatter.format(record)

            parsed = json.loads(formatted_json_str)

            assert parsed["level"] == "INFO"
            assert parsed["request_id"] == "trace-uuid-42"
            assert parsed["user_id"] == 42
            assert parsed["password"] == "[REDACTED]"
            assert parsed["token"] == "[REDACTED]"
            assert parsed["message"] == "User login attempted"
        finally:
            request_id_ctx.reset(token)