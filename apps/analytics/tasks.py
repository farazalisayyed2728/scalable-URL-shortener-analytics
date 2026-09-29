import logging
from typing import Optional
from celery import shared_task
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.analytics.models import Click

logger = logging.getLogger(__name__)


@shared_task(
    name="analytics.record_click_event",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def record_click_event(
    self,
    short_code: str,
    ip_address: Optional[str] = None,
    user_agent: str = "",
    referrer: Optional[str] = None,
    clicked_at_str: Optional[str] = None,
) -> None:
    """
    Background Celery task that ingests a raw click telemetry event.
    Executes asynchronously outside the HTTP redirect lifecycle.
    """
    clicked_at = parse_datetime(clicked_at_str) if clicked_at_str else timezone.now()

    try:
        Click.objects.create(
            short_code=short_code,
            ip_address=ip_address,
            user_agent=user_agent or "",
            referrer=referrer,
            clicked_at=clicked_at,
        )
        logger.info(
            "click_event_ingested",
            extra={"short_code": short_code, "ip": ip_address},
        )
    except Exception as exc:
        logger.error(
            "click_event_ingestion_failed",
            extra={"short_code": short_code, "error": str(exc)},
        )
        # Transient failure retry (e.g. database connection hiccup)
        raise self.retry(exc=exc)
        