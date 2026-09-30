import uuid
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.links.models import ShortURL
from apps.analytics.tasks import record_click_event

User = get_user_model()


@pytest.mark.django_db(transaction=True)
def test_analytics_api_endpoints_and_atomic_counter():
    client = APIClient()

    # 1. Setup authenticated user and link
    user = User.objects.create_user(email="analytics_owner@example.com", password="Password123!")
    link = ShortURL.objects.create(
        short_code="metricstest",
        original_url="https://metrics.example.com",
        owner=user,
        total_clicks=0,
    )

    # 2. Simulate 3 ingested clicks synchronously
    user_agents = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    ]

    for ua in user_agents:
        record_click_event.apply(
            args=[link.short_code, str(uuid.uuid4())],
            kwargs={
                "ip_address": "127.0.0.1",
                "user_agent": ua,
                "referrer": "https://google.com",
            },
        )

    # Invariant check: total_clicks must equal 3
    link.refresh_from_db()
    assert link.total_clicks == 3, f"Expected 3 clicks, got {link.total_clicks}!"

    # 3. Authenticate client
    client.force_authenticate(user=user)

    # 4. Test GET /api/urls/<short_code>/analytics/
    analytics_resp = client.get(f"/api/urls/{link.short_code}/analytics/")
    assert analytics_resp.status_code == 200
    analytics_data = analytics_resp.json()
    assert analytics_data["total_clicks"] == 3
    assert analytics_data["today_clicks"] == 3
    assert analytics_data["devices"]["mobile"] == 1
    assert analytics_data["devices"]["desktop"] == 1
    assert analytics_data["devices"]["bot"] == 1

    # 5. Test GET /api/urls/<short_code>/clicks/ (Cursor Pagination)
    clicks_resp = client.get(f"/api/urls/{link.short_code}/clicks/?page_size=2")
    assert clicks_resp.status_code == 200
    clicks_data = clicks_resp.json()
    assert len(clicks_data["results"]) == 2
    assert clicks_data["next"] is not None

    # 6. Test GET /api/analytics/overview/
    overview_resp = client.get("/api/analytics/overview/")
    assert overview_resp.status_code == 200
    overview_data = overview_resp.json()
    assert overview_data["total_urls"] >= 1
    assert overview_data["total_clicks"] >= 3

    print("\nVerification Passed: Analytics aggregations, F() counter, and Cursor Pagination confirmed!")