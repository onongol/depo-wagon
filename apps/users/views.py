import logging

from allauth.account.adapter import get_adapter
from allauth.core import ratelimit
from django.core.exceptions import ValidationError
from drf_spectacular.utils import OpenApiResponse, extend_schema
from knox.views import LoginView as KnoxLoginView
from knox.views import LogoutAllView as KnoxLogoutAllView
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    expiry = serializers.DateTimeField()


@extend_schema(
    request=LoginSerializer,
    responses={
        200: LoginResponseSerializer,
        400: OpenApiResponse(description="Invalid credentials"),
        429: OpenApiResponse(description="Too many sign-in attempts"),
    },
)
class LoginView(KnoxLoginView):
    """Exchange an email and password for a Knox token.

    Authenticates via allauth's adapter, not Django's ``authenticate()``, so
    attempts here and on the web form share one ``ACCOUNT_RATE_LIMITS`` budget.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, fmt=None):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # Per-IP cap; the per-account one is the adapter's job below.
        if not ratelimit.consume(request, action="login"):
            logger.warning("API login: per-IP rate limit reached")
            raise Throttled

        try:
            user = get_adapter().authenticate(
                request,
                email=email,
                password=serializer.validated_data["password"],
            )
        except ValidationError as exc:
            # Raised when the `login_failed` budget is spent; anything else is a real error.
            if getattr(exc, "code", None) != "too_many_login_attempts":
                raise
            logger.warning("API login: too many failed attempts for %s", email)
            raise Throttled from exc

        # The adapter returns inactive users too (allauth shows them an "account
        # inactive" page); here they must not get a token.
        if not user or not user.is_active:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
            )

        request.user = user
        return super().post(request, fmt)


@extend_schema(
    request=None,
    responses={204: OpenApiResponse(description="Logged out successfully")},
)
class LogoutView(APIView):
    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    request=None,
    responses={204: OpenApiResponse(description="Logged out from all devices")},
)
class LogoutAllView(KnoxLogoutAllView):
    pass
