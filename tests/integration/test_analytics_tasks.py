import pytest
from django.utils import timezone

from apps.analytics.models import Click
from apps.analytics.tasks import record_click_event


@pytest.mark.django_db(transaction=True)
def test_record_click_event_task_execution():
    """
    Verifies that the record_click_event task properly writes to PostgreSQL.
    """

    code = "task_test_99"
    now_str = timezone.now().isoformat()

    result = record_click_event.apply(
        args=[code],
        kwargs={
            "ip_address": "203.0.113.195",
            "user_agent": "Mozilla/5.0 PyTest Runner",
            "referrer": "https://google.com",
            "clicked_at_str": now_str,
        },
    )

    assert result.successful()

    click_entry = Click.objects.get(short_code=code)

    assert click_entry.ip_address == "203.0.113.195"
    assert click_entry.referrer == "https://google.com"
    assert "PyTest" in click_entry.user_agent

    print(
        "\nVerification Passed: "
        "Click recorded successfully in DB via Celery task!"
    )