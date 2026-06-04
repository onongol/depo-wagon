import logging

from apps.ai_service.constants import DocumentStatus
from apps.ai_service.processing.chunking import chunk_page
from apps.ai_service.processing.embedding import embed_text
from apps.ai_service.processing.extraction import extract_pages

logger = logging.getLogger(__name__)


def process_document(document_id: int) -> None:
    """
    Full pipeline: extract text from PDF → chunk → embed with gemini-embedding-2
    → store DocumentChunks. Updates DepotDocument.status throughout.
    """
    from apps.ai_service.models import DepotDocument, DocumentChunk

    doc = DepotDocument.objects.get(pk=document_id)
    doc.status = DocumentStatus.PROCESSING
    doc.error_message = ""
    doc.save(update_fields=["status", "error_message", "updated_at"])

    try:
        doc.chunks.all().delete()

        with doc.file.open("rb") as f:
            pages = extract_pages(f)
        if not pages:
            raise ValueError("No readable text found in document")

        all_chunks: list[dict] = []
        for page_number, page_text in pages:
            all_chunks.extend(chunk_page(page_text, page_number))

        if not all_chunks:
            raise ValueError("Text extraction produced no chunks")

        chunk_objects = []
        for idx, chunk_data in enumerate(all_chunks):
            embedding = embed_text(chunk_data["content"])
            chunk_objects.append(
                DocumentChunk(
                    document=doc,
                    content=chunk_data["content"],
                    embedding=embedding,
                    chunk_index=idx,
                    page_number=chunk_data["page_number"],
                )
            )

        DocumentChunk.objects.bulk_create(chunk_objects)

        doc.status = DocumentStatus.READY
        doc.save(update_fields=["status", "updated_at"])
        logger.info(
            "Document '%s' processed successfully: %d chunks",
            doc.title,
            len(chunk_objects),
        )

    except Exception as exc:
        logger.error(
            "Processing failed for document '%s': %s", doc.title, exc, exc_info=True
        )
        doc.status = DocumentStatus.ERROR
        doc.error_message = str(exc)
        doc.save(update_fields=["status", "error_message", "updated_at"])
        raise
