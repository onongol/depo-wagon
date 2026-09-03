import logging

from django.db import transaction

from apps.ai_service.constants import DocumentStatus
from apps.ai_service.processing.chunking import chunk_page
from apps.ai_service.processing.embedding import embed_texts
from apps.ai_service.processing.extraction import extract_pages

logger = logging.getLogger(__name__)


def process_document(document_id: int) -> None:
    """
    Full pipeline: extract text from PDF → chunk → embed with gemini-embedding-2
    → store DocumentChunks. Updates DepotDocument.status throughout.
    """
    from apps.ai_service.models import DepotDocument, DocumentChunk

    try:
        doc = DepotDocument.objects.get(pk=document_id)
    except DepotDocument.DoesNotExist:
        logger.exception("process_document: document %s not found", document_id)
        return

    doc.status = DocumentStatus.PROCESSING
    doc.error_message = ""
    doc.save(update_fields=["status", "error_message", "updated_at"])

    try:
        with doc.file.open("rb") as f:
            pages = extract_pages(f)
        if not pages:
            raise ValueError("No readable text found in document")

        all_chunks: list[dict[str, str | int]] = []

        for page_number, page_text in pages:
            all_chunks.extend(chunk_page(page_text, page_number))

        if not all_chunks:
            raise ValueError("Text extraction produced no chunks")

        embeddings = embed_texts([chunk["content"] for chunk in all_chunks])
        if len(embeddings) != len(all_chunks):
            raise ValueError(
                f"embed_texts returned {len(embeddings)} embeddings for {len(all_chunks)} chunks"
            )
        chunk_objects = [
            DocumentChunk(
                document=doc,
                content=chunk_data["content"],
                embedding=emb,
                chunk_index=idx,
                page_number=chunk_data["page_number"],
            )
            for idx, (chunk_data, emb) in enumerate(zip(all_chunks, embeddings))
        ]

        with transaction.atomic():
            doc.chunks.all().delete()
            DocumentChunk.objects.bulk_create(chunk_objects)

        doc.status = DocumentStatus.READY
        doc.error_message = ""
        doc.save(update_fields=["status", "error_message", "updated_at"])
        logger.info(
            "Document '%s' processed successfully: %d chunks",
            doc.title,
            len(chunk_objects),
        )

    except Exception as exc:
        logger.exception("Processing failed for document '%s'", doc.title)
        doc.status = DocumentStatus.ERROR
        doc.error_message = str(exc)
        try:
            doc.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            logger.exception(
                "Failed to persist ERROR status for document %s", document_id
            )
        raise
