from django.contrib import admin, messages
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from apps.ai_service.admin.document_chunk import DocumentChunkInline
from apps.ai_service.admin.mixins import (
    DepotDocumentAdminMixinChunksCount,
    DepotDocumentAdminMixinStatus,
)
from apps.ai_service.constants import DocumentStatus
from apps.ai_service.models import DepotDocument


@admin.register(DepotDocument)
class DepotDocumentAdmin(
    DepotDocumentAdminMixinStatus,
    DepotDocumentAdminMixinChunksCount,
    ModelAdmin,
):
    list_display = ("title", "status_badge", "chunks_count", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "description")
    readonly_fields = ("status", "error_message", "created_at", "updated_at")
    inlines = [DocumentChunkInline]
    actions = ["process_documents"]

    def get_queryset(self, request):
        """Annotate with chunks count to avoid N+1 queries in list display."""
        return super().get_queryset(request).annotate(_chunks_count=Count("chunks"))

    def save_model(self, request, obj, form, change):
        """On create or file change, reset status to PENDING and queue processing."""
        from apps.ai_service.tasks import process_document_task

        old_file = (
            DepotDocument.objects.filter(pk=obj.pk)
            .values_list("file", flat=True)
            .first()
            if change
            else None
        )
        super().save_model(request, obj, form, change)

        if not change or (old_file and old_file != obj.file.name):
            obj.status = DocumentStatus.PENDING
            obj.error_message = ""
            obj.save(update_fields=["status", "error_message", "updated_at"])
            process_document_task.delay(obj.pk)

    @admin.action(description=_("Process selected documents (extract & embedding)"))
    def process_documents(self, request, queryset):
        """Queue processing for selected documents that aren't already processing."""
        from apps.ai_service.tasks import process_document_task

        pks = list(
            queryset.exclude(status=DocumentStatus.PROCESSING).values_list(
                "pk", flat=True
            )
        )
        for pk in pks:
            process_document_task.delay(pk)
        queued = len(pks)

        self.message_user(
            request,
            _(
                "%(count)d document(s) queued for processing. Refresh the page to check status."
            )
            % {"count": queued},
            messages.SUCCESS,
        )
