import logging
import random
from typing import Optional

from celery import Task, shared_task
from django.db import IntegrityError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.analytics.models import Click


logger = logging.getLogger(__name__)


class ResilientCallbackTask(Task):
    """
    Custom base Celery Task providing DLQ handling and structured failure hooks.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Executed when a task exhausts all max_retries or encounters
        a non-retryable exception.

        Acts as our Dead Letter Queue (DLQ) handler.
        """
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
                "traceback": str(einfo),
            },
        )

        super().on_failure(
            exc,
            task_id,
            args,
            kwargs,
            einfo,
        )


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
    Resilient background task that logs click events with:

    1. Idempotency guarantees using event_id.
    2. Exponential backoff with full jitter on transient failures.
    3. DLQ quarantine logging after retries are exhausted.
    """

    # -------------------------------------------------------------
    # Step 1: Idempotency verification
    # -------------------------------------------------------------
    if Click.objects.filter(event_id=event_id).exists():
        logger.warning(
            "duplicate_click_event_ignored",
            extra={
                "event_id": event_id,
                "short_code": short_code,
            },
        )
        return

    clicked_at = (
        parse_datetime(clicked_at_str)
        if clicked_at_str
        else timezone.now()
    )

    # -------------------------------------------------------------
    # Step 2: Ingest with controlled retries and jitter
    # -------------------------------------------------------------
    try:
        Click.objects.create(
            event_id=event_id,
            short_code=short_code,
            ip_address=ip_address,
            user_agent=user_agent or "",
            referrer=referrer,
            clicked_at=clicked_at,
        )

        logger.info(
            "click_event_ingested",
            extra={
                "event_id": event_id,
                "short_code": short_code,
            },
        )

    except IntegrityError:
        # Race condition: two identical tasks may pass the
        # existence check concurrently. The DB unique constraint
        # on event_id guarantees only one can be inserted.
        logger.warning(
            "event_id_unique_violation_ignored",
            extra={
                "event_id": event_id,
                "short_code": short_code,
            },
        )
        return

    except Exception as exc:
        current_attempt = self.request.retries + 1

        base_delay = 2

        # Full jitter:
        # sleep = random(0, base_delay * 2^retries)
        max_backoff = base_delay * (2 ** self.request.retries)
        jittered_delay = random.uniform(
            0.5,
            max_backoff,
        )

        logger.warning(
            "click_ingestion_transient_failure_retrying",
            extra={
                "event_id": event_id,
                "short_code": short_code,
                "attempt": current_attempt,
                "max_retries": self.max_retries,
                "backoff_seconds": f"{jittered_delay:.2f}",
                "error": str(exc),
            },
        )

        raise self.retry(
            exc=exc,
            countdown=jittered_delay,
        )


