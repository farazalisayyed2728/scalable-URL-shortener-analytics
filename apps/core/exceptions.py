from typing import Any, Dict, Optional
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


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

class LinkNotFoundException(DomainException):
    code = "LINK_NOT_FOUND"
    message = "The requested short URL does not exist."
    http_status = status.HTTP_404_NOT_FOUND


class LinkExpiredException(DomainException):
    code = "LINK_EXPIRED"
    message = "This short link has expired or has been deactivated."
    http_status = status.HTTP_410_GONE


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    """
    Transforms all exceptions into a consistent error envelope:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Summary description",
            "details": {...}
        }
    }
    """
    # 1. Handle our custom Domain Exceptions directly
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

    # 2. Delegate to DRF's standard handler for framework exceptions (e.g. ValidationError, NotAuthenticated)
    response = exception_handler(exc, context)

    if response is not None:
        error_code = "VALIDATION_ERROR"
        if response.status_code == status.HTTP_404_NOT_FOUND:
            error_code = "NOT_FOUND"
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            error_code = "AUTHENTICATION_REQUIRED"
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            error_code = "PERMISSION_DENIED"
        elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error_code = "RATE_LIMITED"

        # Extract message summary from standard DRF errors
        details = response.data
        message = "Request validation failed."
        if isinstance(details, dict) and "detail" in details:
            message = str(details.pop("detail"))

        response.data = {
            "error": {
                "code": error_code,
                "message": message,
                "details": details if details else None,
            }
        }

    return response