from unfold.admin import TabularInline

from apps.ai_service.admin.mixins import DocumentChunkInlineMixin
from apps.ai_service.models import DocumentChunk


class DocumentChunkInline(TabularInline, DocumentChunkInlineMixin):
    model = DocumentChunk
    fields = ("chunk_index", "page_number", "content_preview")
    readonly_fields = ("chunk_index", "page_number", "content_preview")
    extra = 0
    can_delete = False
    max_num = 0
