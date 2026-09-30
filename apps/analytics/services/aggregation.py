from datetime import timedelta
from typing import Any, Dict
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.analytics.models import Click
from apps.links.models import ShortURL


def get_url_analytics_summary(short_url: ShortURL, days: int = 30) -> Dict[str, Any]:
    """
    Computes dashboard analytics for a single ShortURL instance over a given window.
    """
    now = timezone.now()
    window_start = now - timedelta(days=days)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Base filtered queryset for this URL
    clicks_qs = Click.objects.filter(short_code=short_url.short_code)

    # Clicks today (since 00:00 UTC)
    today_clicks = clicks_qs.filter(clicked_at__gte=today_start).count()

    # Time-window filtered queryset for trends
    window_qs = clicks_qs.filter(clicked_at__gte=window_start)

    # 1. Clicks by Day (Time-Series)
    clicks_by_day = (
        window_qs.annotate(date=TruncDate("clicked_at"))
        .values("date")
        .annotate(clicks=Count("id"))
        .order_by("date")
    )
    formatted_clicks_by_day = [
        {"date": entry["date"].isoformat(), "clicks": entry["clicks"]}
        for entry in clicks_by_day
        if entry["date"] is not None
    ]

    # 2. Top Countries
    top_countries = (
        window_qs.exclude(country_code__isnull=True)
        .exclude(country_code="")
        .values("country_code")
        .annotate(clicks=Count("id"))
        .order_by("-clicks")[:5]
    )

    # 3. Top Referrers
    top_referrers = (
        window_qs.exclude(referrer__isnull=True)
        .exclude(referrer="")
        .values("referrer")
        .annotate(clicks=Count("id"))
        .order_by("-clicks")[:5]
    )

    # 4. Device Breakdown
    device_counts = (
        window_qs.values("device_type")
        .annotate(clicks=Count("id"))
        .order_by("-clicks")
    )
    devices = {entry["device_type"] or "unknown": entry["clicks"] for entry in device_counts}

    return {
        "short_code": short_url.short_code,
        "original_url": short_url.original_url,
        "total_clicks": short_url.total_clicks,
        "today_clicks": today_clicks,
        "window_days": days,
        "clicks_by_day": formatted_clicks_by_day,
        "top_countries": list(top_countries),
        "top_referrers": list(top_referrers),
        "devices": devices,
    }


def get_user_overview_analytics(user) -> Dict[str, Any]:
    """
    Computes aggregated overview analytics across all URLs owned by a user.
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    user_urls = ShortURL.objects.filter(owner=user)
    user_codes = list(user_urls.values_list("short_code", flat=True))

    total_urls = len(user_codes)
    total_clicks = sum(url.total_clicks for url in user_urls)

    clicks_qs = Click.objects.filter(short_code__in=user_codes)
    today_clicks = clicks_qs.filter(clicked_at__gte=today_start).count()

    top_urls = (
        user_urls.order_by("-total_clicks")[:5]
        .values("short_code", "original_url", "total_clicks")
    )

    device_counts = (
        clicks_qs.values("device_type")
        .annotate(clicks=Count("id"))
        .order_by("-clicks")
    )
    devices = {entry["device_type"] or "unknown": entry["clicks"] for entry in device_counts}

    return {
        "total_urls": total_urls,
        "total_clicks": total_clicks,
        "today_clicks": today_clicks,
        "top_urls": list(top_urls),
        "devices": devices,
    }