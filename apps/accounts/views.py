from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.serializers import ErrorEnvelopeSerializer

from .serializers import UserRegistrationSerializer, UserResponseSerializer


class UserRegisterAPIView(APIView):
    """
    Endpoint: POST /api/auth/register/
    Registers a new user account.
    """
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Register a new user",
        description="Creates a new user profile using email and password.",
        request=UserRegistrationSerializer,
        auth=[],
        responses={
            status.HTTP_201_CREATED: UserResponseSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
        },
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        response_serializer = UserResponseSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Obtain JWT token pair",
    description="Authenticates a user and returns access and refresh tokens.",
    tags=["Authentication"],
    auth=[],
)
class UserTokenObtainPairAPIView(TokenObtainPairView):
    pass


@extend_schema(
    summary="Refresh access token",
    description="Exchanges a valid refresh token for a new access token.",
    tags=["Authentication"],
    auth=[],
)
class UserTokenRefreshAPIView(TokenRefreshView):
    pass