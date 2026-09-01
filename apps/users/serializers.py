from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.core.models import Employee

User = get_user_model()


class _EmployeeSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    department_display = serializers.CharField(
        source="get_department_display", read_only=True
    )
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_id",
            "full_name",
            "role",
            "role_display",
            "department",
            "department_display",
        ]


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "is_active", "is_staff"]


class UserSerializer(serializers.ModelSerializer):
    # allow_null: accounts with no Employee row serialize as null, not an error.
    employee = _EmployeeSerializer(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "employee",
        ]
