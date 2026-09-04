import logging

from django.db import transaction

from apps.ai_service.constants import DocumentStatus
from apps.ai_service.processing.chunking import chunk_page
from apps.ai_service.processing.embedding import embed_texts
from apps.ai_service.processing.extraction import extract_pages

logger = logging.getLogger(__name__)


def _extract_and_embed(doc) -> tuple[list[dict[str, str | int]], list[list[float]]]:
    """Extract, chunk and embed a document. Raises ValueError on anything unusable."""
    with doc.file.open("rb") as f:
        pages = extract_pages(f)
    if not pages:
        msg = "No readable text found in document"
        raise ValueError(msg)

    all_chunks: list[dict[str, str | int]] = []
    for page_number, page_text in pages:
        all_chunks.extend(chunk_page(page_text, page_number))

    if not all_chunks:
        msg = "Text extraction produced no chunks"
        raise ValueError(msg)

    embeddings = embed_texts([chunk["content"] for chunk in all_chunks])
    if len(embeddings) != len(all_chunks):
        msg = f"embed_texts returned {len(embeddings)} embeddings for {len(all_chunks)} chunks"
        raise ValueError(msg)

    return all_chunks, embeddings


def _set_status(doc, status: str, error_message: str = "") -> None:
    doc.status = status
    doc.error_message = error_message
    doc.save(update_fields=["status", "error_message", "updated_at"])


def _rebuild_chunks(doc) -> int:
    """Replace the document's chunks with a freshly extracted and embedded set."""
    from apps.ai_service.models import DocumentChunk

    all_chunks, embeddings = _extract_and_embed(doc)
    chunk_objects = [
        DocumentChunk(
            document=doc,
            content=chunk_data["content"],
            embedding=emb,
            chunk_index=idx,
            page_number=chunk_data["page_number"],
        )
        for idx, (chunk_data, emb) in enumerate(
            zip(all_chunks, embeddings, strict=True)
        )
    ]

    with transaction.atomic():
        doc.chunks.all().delete()
        DocumentChunk.objects.bulk_create(chunk_objects)

    return len(chunk_objects)


def process_document(document_id: int) -> None:
    """
    Full pipeline: extract text from PDF → chunk → embed with gemini-embedding-2
    → store DocumentChunks. Updates DepotDocument.status throughout.
    """
    from apps.ai_service.models import DepotDocument

    try:
        doc = DepotDocument.objects.get(pk=document_id)
    except DepotDocument.DoesNotExist:
        logger.exception("process_document: document %s not found", document_id)
        return

    _set_status(doc, DocumentStatus.PROCESSING)

    try:
        chunk_count = _rebuild_chunks(doc)
        _set_status(doc, DocumentStatus.READY)
        logger.info(
            "Document '%s' processed successfully: %d chunks", doc.title, chunk_count
        )
    except Exception as exc:
        logger.exception("Processing failed for document '%s'", doc.title)
        try:
            _set_status(doc, DocumentStatus.ERROR, str(exc))
        except Exception:
            logger.exception(
                "Failed to persist ERROR status for document %s", document_id
            )
        raise
