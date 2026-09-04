from typing import TYPE_CHECKING

from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.ai_service.constants import DocumentStatus

if TYPE_CHECKING:
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
        return obj._chunks_count  # noqa: SLF001 — annotated in get_queryset

    chunks_count.short_description = _("Chunks")
    chunks_count.admin_order_field = "_chunks_count"


_PREVIEW_CHARS = 120


class DocumentChunkInlineMixin:
    def content_preview(self, obj: DocumentChunk) -> str:
        if len(obj.content) <= _PREVIEW_CHARS:
            return obj.content
        return obj.content[:_PREVIEW_CHARS] + "…"

    content_preview.short_description = _("Content preview")
