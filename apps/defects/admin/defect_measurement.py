from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.defects.models import DefectMeasurement


@admin.register(DefectMeasurement)
class DefectMeasurementAdmin(ModelAdmin):
    list_display = [
        "defect",
        "dimension",
        "value",
        "norm_value",
        "unit",
        "created_at",
    ]
    list_filter = ["dimension"]
    search_fields = ["defect", "dimension"]
    readonly_fields = ["created_at", "updated_at"]
