from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.defects.models import DefectMeasurement


@admin.register(DefectMeasurement)
class DefectMeasurementAdmin(ModelAdmin):
    list_display = [
        "defect__wagon__number",
        "dimension",
        "value",
        "norm_value",
        "unit",
        "created_at",
    ]
    list_select_related = ["defect__wagon"]
    list_filter = ["dimension"]
    search_fields = ["defect__wagon__number"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["defect"]
