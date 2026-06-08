from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.defects.models import Defect


@admin.register(Defect)
class DefectAdmin(ModelAdmin):
    list_display = [
        "wagon__number",
        "node",
        "defect_type",
        "severity",
        "status",
        "inspector",
        "verdict",
        "repaired_at",
        "inspected_at",
    ]
    list_select_related = ("wagon", "inspector")
    list_filter = ["node", "defect_type", "severity", "status"]
    search_fields = ["wagon__number"]
    readonly_fields = [
        "ai_recommendation",
        "ai_defect_class",
        "ai_confidence",
        "ai_verdict",
        "created_at",
        "updated_at",
    ]
