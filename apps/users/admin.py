from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.users.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(ModelAdmin):
    list_display = [
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    ]
    list_filter = ["is_staff", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["date_joined", "last_login"]

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and hasattr(obj, "employee"):
            return [*self.readonly_fields, "is_active"]
        return self.readonly_fields
