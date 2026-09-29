from unittest.mock import patch

import pytest
from django.conf import settings

from apps.core.exceptions import LinkNotFoundException
from apps.links.services.resolver import resolve_short_code


def test_negative_cache_hit_raises_link_not_found():
    with patch(
        "apps.links.services.cache.redis_client.get",
        return_value=settings.NEGATIVE_CACHE_SENTINEL,
    ):
        with pytest.raises(LinkNotFoundException):
            resolve_short_code("missing")
