from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.core.models import Employee


@admin.register(Employee)
class EmployeeAdmin(ModelAdmin):
    list_display = [
        "employee_id",
        "first_name",
        "last_name",
        "role",
        "telegram_id",
        "user",
        "phone",
        "email",
        "is_active",
        "created_at",
        "updated_at",
    ]
    list_filter = ["role", "is_active"]
    search_fields = ["employee_id", "first_name", "last_name", "email", "phone"]
    readonly_fields = ["created_at", "updated_at"]
