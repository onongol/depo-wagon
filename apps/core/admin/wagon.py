from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.core.models import Wagon


@admin.register(Wagon)
class WagonAdmin(ModelAdmin):
    list_display = [
        "number",
        "wagon_type",
        "manufacture_year",
        "last_repair_date",
        "next_repair_date",
        "mileage_km",
        "owner",
        "status",
        "repair_type",
        "needs_repair_soon",
    ]
    list_filter = ["status", "wagon_type", "repair_type"]
    search_fields = ["number", "owner"]
    readonly_fields = ["created_at", "updated_at"]
