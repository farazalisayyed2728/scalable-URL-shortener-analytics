import ipaddress
import re
import socket
from urllib.parse import urlparse
from django.conf import settings
from apps.core.exceptions import URLValidationException

CUSTOM_CODE_REGEX = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def _is_ip_address_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """
    Evaluates whether an IP address belongs to internal, private, loopback,
    link-local, or reserved network boundaries.
    """
    return any(
        [
            ip.is_private,      # 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
            ip.is_loopback,     # 127.0.0.0/8, ::1
            ip.is_link_local,   # 169.254.0.0/16 (AWS/Cloud Metadata Service)
            ip.is_reserved,     # IETF reserved ranges
            ip.is_multicast,    # 224.0.0.0/4
            ip.is_unspecified,  # 0.0.0.0, ::
        ]
    )


def validate_original_url(url: str) -> str:
    """
    Validates URL syntax, length, supported schemes, prevents self-referencing loops,
    and defends against SSRF by blocking private and internal IP ranges.
    """
    if not url:
        raise URLValidationException("URL cannot be empty.")

    if len(url) > settings.MAX_URL_LENGTH:
        raise URLValidationException(
            f"URL exceeds maximum allowed length of {settings.MAX_URL_LENGTH} characters."
        )

    parsed = urlparse(url)

    # 1. Protocol Scheme Enforcement: Strictly allow http and https only
    if parsed.scheme.lower() not in ("http", "https"):
        raise URLValidationException(
            f"Scheme '{parsed.scheme}' is prohibited. Only 'http' and 'https' protocols are permitted."
        )

    # 2. Host Validation: Must possess a valid hostname
    hostname = parsed.hostname
    if not hostname:
        raise URLValidationException("The provided URL has an invalid or missing host.")

    # 3. Prevent Self-Referencing Redirect Loops
    base_domain = urlparse(settings.BASE_SHORT_URL).netloc.lower()
    if parsed.netloc.lower() == base_domain:
        raise URLValidationException("Shortening URLs targeting this service domain is prohibited.")

    # 4. SSRF Defense: Validate Host Against Private Subnets & Loopbacks
    if getattr(settings, "BLOCK_PRIVATE_IPS", True):
        # Case A: Hostname is directly a raw IPv4 or IPv6 address
        try:
            raw_ip = ipaddress.ip_address(hostname)
            if _is_ip_address_blocked(raw_ip):
                raise URLValidationException(
                    "Target URL resolves to a restricted internal or loopback IP address."
                )
            return url
        except ValueError:
            # Hostname is a standard domain name (e.g. google.com), proceed to DNS check
            pass

        # Case B: Resolve Domain via DNS and Inspect All Bound IP Addresses
        try:
            # getaddrinfo resolves both IPv4 and IPv6 addresses
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                sockaddr = item[4]
                resolved_ip_str = sockaddr[0]
                resolved_ip = ipaddress.ip_address(resolved_ip_str)

                if _is_ip_address_blocked(resolved_ip):
                    raise URLValidationException(
                        "Target domain resolves to a restricted internal or loopback IP address."
                    )
        except socket.gaierror:
            raise URLValidationException(
                f"Target domain '{hostname}' could not be resolved via DNS."
            )

    return url


def validate_custom_code(custom_code: str) -> str:
    """
    Validates custom short-code format and prevents squatting on reserved system keywords.
    """
    if not CUSTOM_CODE_REGEX.match(custom_code):
        raise URLValidationException(
            "Custom code must be 3-32 characters long and contain only letters, numbers, hyphens, and underscores."
        )

    if custom_code.lower() in settings.RESERVED_CODES:
        raise URLValidationException(
            f"'{custom_code}' is a reserved system keyword and cannot be used."
        )

    return custom_code