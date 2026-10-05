from unittest.mock import patch
import pytest
import redis
from django.conf import settings
from apps.links.models import ShortURL
from apps.links.services.cache import (
    cache_not_found,
    cache_url,
    delete_cached_url,
    get_cached_url_data,
)
from apps.links.services.resolver import resolve_short_code


@pytest.mark.django_db(transaction=True)
class TestCacheResilienceAndGracefulDegradation:

    def test_redis_get_failure_falls_back_cleanly(self):
        """Verify that a RedisError on cache read returns None and falls back to DB."""
        link = ShortURL.objects.create(
            short_code="redis_down_test",
            original_url="https://resilience.org",
            is_active=True,
        )

        # Force redis client.get to raise a network connection error
        with patch("redis.Redis.get", side_effect=redis.ConnectionError("Redis connection refused")):
            # Cache lookup should safely return None (graceful degradation)
            cached_data = get_cached_url_data(link.short_code)
            assert cached_data is None

            # High-level resolver must still succeed by reading PostgreSQL directly
            resolved_url = resolve_short_code(link.short_code)
            assert resolved_url == "https://resilience.org"

    def test_redis_set_failure_does_not_break_execution(self):
        """Verify that a RedisError on cache write logs a warning but does not raise an exception."""
        with patch("redis.Redis.set", side_effect=redis.TimeoutError("Redis socket write timeout")):
            # Must not raise an exception
            cache_url(
                short_code="fail_set",
                original_url="https://example.com",
                is_active=True,
                expires_at=None,
            )

    def test_cached_url_data_hit_returns_decoded_payload(self):
        payload = '{"original_url": "https://example.com"}'
        with patch("redis.Redis.get", return_value=payload):
            assert get_cached_url_data("cached_code") == {
                "original_url": "https://example.com"
            }

    def test_negative_cache_is_written(self):
        with patch("redis.Redis.set") as set_value:
            cache_not_found("missing_code")

        set_value.assert_called_once_with(
            "short:missing_code",
            settings.NEGATIVE_CACHE_SENTINEL,
            ex=settings.NEGATIVE_CACHE_TTL_SECONDS,
        )

    def test_negative_cache_failure_logs_warning(self, caplog):
        with patch(
            "redis.Redis.set",
            side_effect=redis.TimeoutError("Redis socket write timeout"),
        ):
            cache_not_found("missing_code")

        assert "Redis negative cache failed" in caplog.text

    def test_delete_cache_failure_logs_warning(self, caplog):
        with patch(
            "redis.Redis.delete",
            side_effect=redis.ConnectionError("Redis connection refused"),
        ):
            delete_cached_url("cached_code")

        assert "Redis DELETE failed" in caplog.text