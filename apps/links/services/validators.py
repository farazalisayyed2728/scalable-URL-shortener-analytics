import re
from urllib.parse import urlparse
from django.conf import settings
from apps.core.exceptions import URLValidationException

CUSTOM_CODE_REGEX = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def validate_original_url(url: str) -> str:
    """
    Validates URL syntax, length, supported schemes, and prevents self-referencing loops.
    """
    if not url:
        raise URLValidationException("URL cannot be empty.")

    if len(url) > settings.MAX_URL_LENGTH:
        raise URLValidationException(f"URL exceeds maximum allowed length of {settings.MAX_URL_LENGTH} characters.")

    parsed = urlparse(url)

    # 1. Scheme enforcement: Only http and https allowed
    if parsed.scheme.lower() not in ("http", "https"):
        raise URLValidationException("Only 'http' and 'https' protocols are permitted.")

    # 2. Host validation: URL must possess a valid network location
    if not parsed.netloc:
        raise URLValidationException("The provided URL has an invalid or missing host.")

    # 3. Prevent self-referential redirect loops
    base_domain = urlparse(settings.BASE_SHORT_URL).netloc.lower()
    if parsed.netloc.lower() == base_domain:
        raise URLValidationException("Shortening URLs targeting this service domain is prohibited.")

    return url


def validate_custom_code(custom_code: str) -> str:
    """
    Validates custom short-code format and prevents squatting on reserved system routes.
    """
    if not CUSTOM_CODE_REGEX.match(custom_code):
        raise URLValidationException(
            "Custom code must be 3-32 characters long and contain only letters, numbers, hyphens, and underscores."
        )

    if custom_code.lower() in settings.RESERVED_CODES:
        raise URLValidationException(f"'{custom_code}' is a reserved system keyword and cannot be used.")

    return custom_code