from rest_framework import serializers


class ErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField(
        help_text="Standardized machine-readable error code (e.g., VALIDATION_ERROR, RATE_LIMITED)."
    )
    message = serializers.CharField(
        help_text="Human-readable summary description of the error."
    )
    details = serializers.DictField(
        required=False,
        allow_null=True,
        help_text="Detailed field-level validation errors or metadata, if applicable.",
    )


class ErrorEnvelopeSerializer(serializers.Serializer):
    """
    Standardized project-wide error response schema.
    """
    error = ErrorBodySerializer()