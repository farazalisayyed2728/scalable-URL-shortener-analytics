from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ShortURLCreateRequestSerializer,
    ShortURLResponseSerializer,
)
from .services.shortener import create_short_url


class ShortURLCreateAPIView(APIView):
    """
    Endpoint: POST /api/urls/
    Creates a new short URL. Open to both anonymous and authenticated users.
    """
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        # 1. Validate payload structure using Serializer
        serializer = ShortURLCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        owner = request.user if request.user.is_authenticated else None

        # 2. Delegate creation, collision handling, and DB storage to Service Layer
        short_url_instance = create_short_url(
            original_url=validated_data["original_url"],
            owner=owner,
            custom_code=validated_data.get("custom_code"),
            expires_at=validated_data.get("expires_at"),
        )

        # 3. Serialize response model
        response_serializer = ShortURLResponseSerializer(short_url_instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)