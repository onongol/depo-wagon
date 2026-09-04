import logging

from celery import shared_task
from django.db import IntegrityError, transaction

logger = logging.getLogger(__name__)


def _build_defect_texts(defect) -> tuple[str, str]:
    """Query text to embed, and the content blob stored alongside the vector."""
    node = defect.get_node_display()
    defect_type = defect.get_defect_type_display()
    severity = defect.get_severity_display()

    query_text = "\n".join(
        filter(
            None,
            [
                f"Node: {node}",
                f"Defect type: {defect_type}",
                f"Severity: {severity}",
                f"Description: {defect.description}" if defect.description else None,
            ],
        )
    )

    content_parts = [f"Defect: {node} — {defect_type} ({severity})"]
    if defect.description:
        content_parts.append(f"Description: {defect.description}")
    if defect.verdict:
        content_parts.append(f"Verdict: {defect.get_verdict_display()}")
    if defect.ai_recommendation:
        content_parts.append(f"Recommendation: {defect.ai_recommendation}")

    return query_text, "\n".join(content_parts)


def _store_vector(defect_id: str, content: str, embedding: list[float]) -> None:
    """Upsert the defect vector, falling back to an update on a concurrent insert."""
    from apps.ai_service.models import DefectVector

    try:
        with transaction.atomic():
            DefectVector.objects.update_or_create(
                defect_id=defect_id,
                defaults={"content": content, "embedding": embedding},
            )
    except IntegrityError:
        DefectVector.objects.filter(defect_id=defect_id).update(
            content=content, embedding=embedding
        )


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="ai_service.embed_defect",
)
def embed_defect_task(self, defect_id: str) -> None:
    from apps.defects.models import Defect

    defect = Defect.objects.select_related("wagon").get(pk=defect_id)

    if not defect.verdict:
        logger.info("No verdict yet for defect %s, retrying in 30s", defect_id)
        raise self.retry(countdown=30)

    try:
        from apps.ai_service.processing.embedding import embed_texts

        query_text, content = _build_defect_texts(defect)
        [embedding] = embed_texts([query_text], task_type="RETRIEVAL_DOCUMENT")
        _store_vector(defect_id, content, embedding)
        logger.info("Embedded defect %s for historical RAG", defect_id)

    except Exception as exc:
        logger.exception("embed_defect_task failed for %s", defect_id)
        raise self.retry(exc=exc) from exc
