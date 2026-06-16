from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from apps.ai_service.models import DefectVector


@admin.register(DefectVector)
class DefectVectorAdmin(ModelAdmin):
    list_display = ("defect", "defect_node", "defect_type", "created_at")
    search_fields = ("defect__wagon__number",)
    readonly_fields = ("defect", "content", "created_at")
    exclude = ("embedding",)
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("defect__wagon")

    @admin.display(description=_("Node"))
    def defect_node(self, obj):
        return obj.defect.get_node_display()

    @admin.display(description=_("Defect type"))
    def defect_type(self, obj):
        return obj.defect.get_defect_type_display()
