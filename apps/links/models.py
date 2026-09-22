from django.conf import settings
from django.db import models
from django.utils import timezone


class ShortURL(models.Model):
    id = models.BigAutoField(primary_key=True)

    short_code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True
    )

    original_url = models.URLField(max_length=2048)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="short_urls",
    )

    is_custom = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    total_clicks = models.BigIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "links_shorturl"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["owner", "-created_at"],
                name="idx_shorturl_owner_created",
            ),
        ]

    def __str__(self):
        return f"{self.short_code} -> {self.original_url[:30]}"

    @property
    def is_expired(self) -> bool:
        if self.expires_at is not None:
            return timezone.now() >= self.expires_at

        return False