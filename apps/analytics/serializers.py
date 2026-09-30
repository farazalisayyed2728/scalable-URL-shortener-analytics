from rest_framework import serializers
from apps.analytics.models import Click


class ClickLogSerializer(serializers.ModelSerializer):
    """
    Serializes raw Click records for cursor-paginated event auditing.
    Omits raw IP addresses to protect user privacy.
    """
    class Meta:
        model = Click
        fields = [
            "id",
            "short_code",
            "clicked_at",
            "country_code",
            "device_type",
            "browser",
            "os",
            "referrer",
            "is_bot",
        ]


class URLAnalyticsResponseSerializer(serializers.Serializer):
    short_code = serializers.CharField()
    original_url = serializers.CharField()
    total_clicks = serializers.IntegerField()
    today_clicks = serializers.IntegerField()
    window_days = serializers.IntegerField()
    clicks_by_day = serializers.ListField()
    top_countries = serializers.ListField()
    top_referrers = serializers.ListField()
    devices = serializers.DictField()


class UserOverviewAnalyticsResponseSerializer(serializers.Serializer):
    total_urls = serializers.IntegerField()
    total_clicks = serializers.IntegerField()
    today_clicks = serializers.IntegerField()
    top_urls = serializers.ListField()
    devices = serializers.DictField()