import uuid
from unittest.mock import patch

import pytest

from apps.analytics.models import Click
from apps.analytics.tasks import record_click_event


@pytest.mark.django_db(transaction=True)
class TestTaskResilienceAndIdempotency:
    def test_idempotent_duplicate_event_handling(self):
        event_id = str(uuid.uuid4())
        args = ["idempotent_test", event_id]
        kwargs = {
            "ip_address": "127.0.0.1",
            "user_agent": "TestBrowser",
        }

        record_click_event.apply(args=args, kwargs=kwargs)
        record_click_event.apply(args=args, kwargs=kwargs)

        assert Click.objects.filter(event_id=event_id).count() == 1

    def test_controlled_retry_and_dlq_on_persistent_failure(self):
        event_id = str(uuid.uuid4())

        with (
            patch(
                "apps.analytics.models.Click.objects.create",
                side_effect=RuntimeError("DB Connection Lost"),
            ) as mock_create,
            patch(
                "apps.analytics.tasks.random.uniform",
                side_effect=lambda minimum, maximum: maximum,
            ) as mock_backoff,
            patch.object(record_click_event, "on_failure") as mock_dlq,
        ):
            result = record_click_event.apply(
                args=["fail_code", event_id],
                throw=False,
            )

        assert result.failed()
        assert isinstance(result.result, RuntimeError)
        assert mock_create.call_count == record_click_event.max_retries + 1
        assert mock_backoff.call_args_list == [
            ((0, 2),),
            ((0, 4),),
            ((0, 8),),
        ]
        mock_dlq.assert_called_once()
