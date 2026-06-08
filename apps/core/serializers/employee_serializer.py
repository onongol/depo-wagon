from rest_framework import serializers

from apps.core.models import Employee


class EmployeeListSerializer(serializers.ModelSerializer):
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
            "is_active",
        ]


class EmployeeSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    department_display = serializers.CharField(
        source="get_department_display", read_only=True
    )
    full_name = serializers.CharField(read_only=True)
    short_name = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_id",
            "first_name",
            "last_name",
            "full_name",
            "short_name",
            "role",
            "role_display",
            "department",
            "department_display",
            "telegram_id",
            "user",
            "phone",
            "email",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
