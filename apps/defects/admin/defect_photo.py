from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.defects.models import DefectPhoto


@admin.register(DefectPhoto)
class DefectPhotoAdmin(ModelAdmin):
    list_display = [
        "defect",
        "uploaded_at",
    ]
    list_filter = ["defect"]
    readonly_fields = ["uploaded_at"]
