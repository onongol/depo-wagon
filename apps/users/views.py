from django.contrib.auth import authenticate
from drf_spectacular.utils import OpenApiResponse, extend_schema
from knox.views import LoginView as KnoxLoginView
from knox.views import LogoutAllView as KnoxLogoutAllView
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


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
    },
)
class LoginView(KnoxLoginView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, fmt=None):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if not user:
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
