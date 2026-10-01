import logging
from typing import Any, Dict, Optional
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class DomainException(Exception):
    """Base exception for application-level domain errors."""
    code = "INTERNAL_ERROR"
    message = "An unexpected error occurred."
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if message:
            self.message = message
        self.details = details or {}
        super().__init__(self.message)


class LinkNotFoundException(DomainException):
    code = "LINK_NOT_FOUND"
    message = "The requested short URL does not exist."
    http_status = status.HTTP_404_NOT_FOUND


class LinkExpiredException(DomainException):
    code = "LINK_EXPIRED"
    message = "This short link has expired or has been deactivated."
    http_status = status.HTTP_410_GONE


class CodeAlreadyTakenException(DomainException):
    code = "CODE_ALREADY_TAKEN"
    message = "The requested custom short code is already in use."
    http_status = status.HTTP_409_CONFLICT


class CodeGenerationFailedException(DomainException):
    code = "CODE_GENERATION_FAILED"
    message = "Unable to allocate a unique short code. Please try again."
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE


class URLValidationException(DomainException):
    code = "INVALID_URL"
    message = "The submitted URL failed safety or syntax validation."
    http_status = status.HTTP_400_BAD_REQUEST


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    """
    Unified project exception handler. Enforces:
    {
        "error": {
            "code": "STRING_IDENTIFIER",
            "message": "Human-readable summary",
            "details": {...} or null
        }
    }
    Guarantees no raw Python tracebacks or internal SQL details leak in 500 responses.
    """
    # -------------------------------------------------------------
    # 1. Custom Domain Exceptions
    # -------------------------------------------------------------
    if isinstance(exc, DomainException):
        return Response(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details if exc.details else None,
                }
            },
            status=exc.http_status,
        )

    # -------------------------------------------------------------
    # 2. Django Built-in Exceptions (Http404, PermissionDenied)
    # -------------------------------------------------------------
    if isinstance(exc, Http404):
        return Response(
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": str(exc) or "The requested resource was not found.",
                    "details": None,
                }
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, PermissionDenied):
        return Response(
            {
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": str(exc) or "You do not have permission to perform this action.",
                    "details": None,
                }
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # -------------------------------------------------------------
    # 3. Standard DRF Exceptions
    # -------------------------------------------------------------
    response = exception_handler(exc, context)

    if response is not None:
        error_code = "API_ERROR"
        message = "An error occurred while processing your request."
        details = response.data

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_code = "VALIDATION_ERROR"
            message = "Request validation failed."
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            error_code = "AUTHENTICATION_REQUIRED"
            message = "Authentication credentials were not provided or are invalid."
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            error_code = "PERMISSION_DENIED"
            message = "You do not have permission to access this resource."
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            error_code = "NOT_FOUND"
            message = "The requested resource does not exist."
        elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            error_code = "METHOD_NOT_ALLOWED"
            message = f"HTTP method '{context['request'].method}' is not supported on this endpoint."
        elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error_code = "RATE_LIMITED"
            wait_seconds = getattr(exc, "wait", None)
            if wait_seconds:
                message = f"Too many requests. Try again in {int(wait_seconds)} seconds."
            else:
                message = "Too many requests. Please slow down."

        # Extract message if DRF provided a string "detail"
        if isinstance(details, dict) and "detail" in details:
            custom_detail = str(details.pop("detail"))
            if error_code != "VALIDATION_ERROR":
                message = custom_detail

        response.data = {
            "error": {
                "code": error_code,
                "message": message,
                "details": details if details else None,
            }
        }
        return response

    # -------------------------------------------------------------
    # 4. Unhandled 500 Exceptions (Shielding & Structured Logging)
    # -------------------------------------------------------------
    request = context.get("request")
    request_id = getattr(request, "request_id", "no_request_id") if request else "no_request_id"

    logger.error(
        "unhandled_server_exception",
        exc_info=exc,
        extra={
            "request_id": request_id,
            "path": getattr(request, "path", "unknown"),
            "method": getattr(request, "method", "unknown"),
        },
    )

    return Response(
        {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal error occurred. Please try again later.",
                "details": None,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )