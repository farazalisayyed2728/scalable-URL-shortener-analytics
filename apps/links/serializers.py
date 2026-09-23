from django.conf import settings
from rest_framework import serializers


class ShortURLCreateRequestSerializer(serializers.Serializer):
    """
    Validates the incoming HTTP request payload.
    """
    original_url = serializers.URLField(max_length=2048, required=True)
    custom_code = serializers.CharField(
        max_length=32,
        required=False,
        allow_null=True,
        allow_blank=False,
        default=None,
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True, default=None)

    def validate_expires_at(self, value):
        from django.utils import timezone
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiration date must be in the future.")
        return value


class ShortURLResponseSerializer(serializers.Serializer):
    """
    Serializes ShortURL model instances to the outgoing JSON contract.
    """
    id = serializers.IntegerField(read_only=True)
    short_code = serializers.CharField(read_only=True)
    short_url = serializers.SerializerMethodField()
    original_url = serializers.CharField(read_only=True)
    is_custom = serializers.BooleanField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def get_short_url(self, obj) -> str:
        # Constructs: http://localhost:8000/<short_code>
        base = settings.BASE_SHORT_URL.rstrip("/")
        return f"{base}/{obj.short_code}"