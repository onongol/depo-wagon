from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.defects.models import DefectPhoto


@admin.register(DefectPhoto)
class DefectPhotoAdmin(ModelAdmin):
    list_display = [
        "defect__wagon__number",
        "uploaded_at",
    ]
    list_select_related = ["defect__wagon"]
    search_fields = [
        "defect__wagon__number",
    ]
    readonly_fields = ["uploaded_at"]
    raw_id_fields = ["defect"]
