from urllib.parse import urlparse

import pytest
from django.conf import settings

from apps.core.exceptions import URLValidationException
from apps.links.services.validators import validate_original_url


class TestSecurityValidators:

    @pytest.mark.parametrize(
        "dangerous_scheme",
        [
            "javascript:alert(document.cookie)",
            "file:///etc/passwd",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
            "gopher://127.0.0.1:6379/_FLUSHALL",
            "ftp://files.internal.corp",
        ],
    )
    def test_prohibited_schemes_rejected(self, dangerous_scheme: str):
        """Verify that non-http/https protocol schemes are strictly blocked."""
        with pytest.raises(URLValidationException) as exc_info:
            validate_original_url(dangerous_scheme)
        assert "is prohibited" in str(exc_info.value.message)

    @pytest.mark.parametrize(
        "internal_target",
        [
            "http://127.0.0.1/admin",
            "http://127.0.0.1:5432",
            "http://10.0.0.1/config",
            "http://192.168.1.1/router",
            "http://172.16.0.5/api",
            "http://169.254.169.254/latest/meta-data/",
            "http://0.0.0.0:8000",
            "http://localhost:8000/internal",
        ],
    )
    def test_private_and_loopback_ips_blocked(self, internal_target: str):
        """Verify that private subnets, loopbacks, and cloud metadata addresses are rejected."""
        with pytest.raises(URLValidationException) as exc_info:
            validate_original_url(internal_target)
        message = str(exc_info.value.message).lower()
        assert "restricted" in message or "service domain" in message

    def test_service_domain_blocked_on_any_port(self):
        base_url = urlparse(settings.BASE_SHORT_URL)
        hostname = base_url.hostname
        assert hostname is not None
        if ":" in hostname:
            hostname = f"[{hostname}]"
        target = f"{base_url.scheme}://{hostname}:9999/internal"

        with pytest.raises(URLValidationException) as exc_info:
            validate_original_url(target)

        assert "service domain" in str(exc_info.value.message).lower()

    def test_valid_public_url_accepted(self):
        """Verify that legitimate public targets pass validation without errors."""
        valid_url = "https://www.python.org/downloads/"
        assert validate_original_url(valid_url) == valid_url