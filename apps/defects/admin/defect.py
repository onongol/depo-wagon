from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.defects.models import Defect


@admin.register(Defect)
class DefectAdmin(ModelAdmin):
    list_display = [
        "wagon",
        "node",
        "defect",
        "severity",
        "status",
        "inspector",
        "verdict",
        "repaired_at",
        "inspected_at",
    ]
    list_filter = ["node", "defect", "severity", "status"]
    search_fields = ["wagon"]
    readonly_fields = [
        "ai_recommendation",
        "ai_defect_class",
        "ai_confidence",
        "ai_verdict",
        "created_at",
        "updated_at",
    ]
