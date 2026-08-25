from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.ai_service.constants import DocumentStatus
from apps.ai_service.models import DepotDocument, DocumentChunk


class DepotDocumentAdminMixinStatus:
    def status_badge(self, obj: DepotDocument) -> str:
        colors = {
            DocumentStatus.PENDING: "#6b7280",
            DocumentStatus.PROCESSING: "#f59e0b",
            DocumentStatus.READY: "#10b981",
            DocumentStatus.ERROR: "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = _("Status")


class DepotDocumentAdminMixinChunksCount:
    def chunks_count(self, obj: DepotDocument) -> int:
        return obj._chunks_count

    chunks_count.short_description = _("Chunks")
    chunks_count.admin_order_field = "_chunks_count"


class DocumentChunkInlineMixin:
    def content_preview(self, obj: DocumentChunk) -> str:
        return obj.content[:120] + "…" if len(obj.content) > 120 else obj.content

    content_preview.short_description = _("Content preview")
