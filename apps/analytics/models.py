import uuid

from django.db import models
from django.utils import timezone


class Click(models.Model):
    id = models.BigAutoField(primary_key=True)

    # Idempotency token: prevents duplicate logging on task re-delivery
    event_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
    )

    short_code = models.CharField(max_length=32)
    clicked_at = models.DateTimeField(default=timezone.now)

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    user_agent = models.TextField(
        blank=True,
        default="",
    )

    referrer = models.CharField(
        max_length=2048,
        null=True,
        blank=True,
    )

    country_code = models.CharField(
        max_length=2,
        null=True,
        blank=True,
    )

    device_type = models.CharField(
        max_length=16,
        null=True,
        blank=True,
    )

    browser = models.CharField(
        max_length=32,
        null=True,
        blank=True,
    )

    os = models.CharField(
        max_length=32,
        null=True,
        blank=True,
    )

    is_bot = models.BooleanField(default=False)

    class Meta:
        db_table = "analytics_click"

        indexes = [
            models.Index(
                fields=["short_code", "-clicked_at"],
                name="idx_click_code_clicked",
            ),
            models.Index(
                fields=["-clicked_at"],
                name="idx_click_clicked_at",
            ),
        ]

    def __str__(self):
        return f"Click: {self.short_code} ({self.event_id})"