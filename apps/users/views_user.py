from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAdminUser

from apps.users.serializers import UserListSerializer, UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve accounts. Sign-up and password changes stay in allauth."""

    queryset = User.objects.select_related("employee").all()
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "is_staff", "is_superuser"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["email", "date_joined", "last_login"]
    ordering = ["email"]

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        return UserSerializer
