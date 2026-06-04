import threading

from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from apps.ai_service.admin.document_chunk import DocumentChunkInline
from apps.ai_service.admin.mixins import (
    DepotDocumentAdminMixinChunksCount,
    DepotDocumentAdminMixinStatus,
)
from apps.ai_service.admin.utils import run_processing
from apps.ai_service.constants import DocumentStatus
from apps.ai_service.models import DepotDocument


@admin.register(DepotDocument)
class DepotDocumentAdmin(
    ModelAdmin, DepotDocumentAdminMixinStatus, DepotDocumentAdminMixinChunksCount
):
    list_display = ("title", "status_badge", "chunks_count", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "description")
    readonly_fields = ("status", "error_message", "created_at", "updated_at")
    inlines = [DocumentChunkInline]
    actions = ["process_documents"]

    def save_model(self, request, obj, form, change):
        """When a document is created or its file is changed, reset status to PENDING and trigger processing."""
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
            thread = threading.Thread(
                target=run_processing, args=(obj.pk,), daemon=True
            )
            thread.start()

    @admin.action(description=_("Process selected documents (extract & embedding)"))
    def process_documents(self, request, queryset):
        """Trigger processing for selected documents that aren't already processing."""
        queued = 0
        for doc in queryset.exclude(status=DocumentStatus.PROCESSING):
            thread = threading.Thread(
                target=run_processing, args=(doc.pk,), daemon=True
            )
            thread.start()
            queued += 1

        self.message_user(
            request,
            _(
                f"{queued} document(s) queued for processing. Refresh the page to check status."
            ),
            messages.SUCCESS,
        )
