from celery import Task, shared_task
from django.db import IntegrityError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.analytics.models import Click

import logging
import random
from typing import Optional
from celery import Task, shared_task
from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.analytics.models import Click
from apps.analytics.services.enrichment import parse_user_agent_metadata
from apps.links.models import ShortURL

logger = logging.getLogger(__name__)


class ResilientCallbackTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        event_id = kwargs.get("event_id")
        short_code = kwargs.get("short_code")
        logger.critical(
            "task_dead_letter_quarantine",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "event_id": event_id,
                "short_code": short_code,
                "exception": str(exc),
            },
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(
    name="analytics.record_click_event",
    base=ResilientCallbackTask,
    bind=True,
    max_retries=3,
    acks_late=True,
)
def record_click_event(
    self,
    short_code: str,
    event_id: str,
    ip_address: Optional[str] = None,
    user_agent: str = "",
    referrer: Optional[str] = None,
    clicked_at_str: Optional[str] = None,
) -> None:
    """
    Ingests click event:
    1. Enforces idempotency via event_id.
    2. Enriches User-Agent metadata (device, browser, os, is_bot).
    3. Persists Click record.
    4. Atomically increments ShortURL.total_clicks via database F() expression.
    """
    # 1. Idempotency Check
    if Click.objects.filter(event_id=event_id).exists():
        logger.warning(
            "duplicate_click_event_ignored",
            extra={"event_id": event_id, "short_code": short_code},
        )
        return

    clicked_at = parse_datetime(clicked_at_str) if clicked_at_str else timezone.now()

    # 2. Enrich Metadata
    enrichment = parse_user_agent_metadata(user_agent)

    # 3. Insert Click Record
    try:
        Click.objects.create(
            event_id=event_id,
            short_code=short_code,
            ip_address=ip_address,
            user_agent=user_agent or "",
            referrer=referrer,
            clicked_at=clicked_at,
            device_type=enrichment["device_type"],
            browser=enrichment["browser"],
            os=enrichment["os"],
            is_bot=enrichment["is_bot"],
        )
        
        # 4. Atomic Counter Increment (Prevents Lost Updates)
        ShortURL.objects.filter(short_code=short_code).update(
            total_clicks=F("total_clicks") + 1
        )

        logger.info(
            "click_event_ingested",
            extra={"event_id": event_id, "short_code": short_code},
        )
    except IntegrityError:
        logger.warning(
            "event_id_unique_violation_ignored",
            extra={"event_id": event_id, "short_code": short_code},
        )
        return
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            raise

        base_delay = 2
        max_backoff = base_delay * (2 ** self.request.retries)
        jittered_delay = random.uniform(0.5, max_backoff)
        raise self.retry(exc=exc, countdown=jittered_delay)