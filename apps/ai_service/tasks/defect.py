import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="ai_service.embed_defect",
)
def embed_defect_task(self, defect_id: str) -> None:
    try:
        from apps.ai_service.models import DefectVector
        from apps.ai_service.processing.embedding import embed_texts
        from apps.defects.models import Defect

        defect = Defect.objects.select_related("wagon").get(pk=defect_id)

        query_text = "\n".join(
            filter(
                None,
                [
                    f"Узел: {defect.get_node_display()}",
                    f"Тип дефекта: {defect.get_defect_type_display()}",
                    f"Степень: {defect.get_severity_display()}",
                    f"Описание: {defect.description}" if defect.description else None,
                ],
            )
        )

        content_parts = [
            f"Дефект: {defect.get_node_display()} — {defect.get_defect_type_display()} ({defect.get_severity_display()})",
        ]
        if defect.description:
            content_parts.append(f"Описание: {defect.description}")
        if defect.verdict:
            content_parts.append(f"Вердикт: {defect.get_verdict_display()}")
        if defect.ai_recommendation:
            content_parts.append(f"Рекомендация: {defect.ai_recommendation}")

        content = "\n".join(content_parts)

        [embedding] = embed_texts([query_text], task_type="RETRIEVAL_DOCUMENT")

        DefectVector.objects.update_or_create(
            defect_id=defect_id,
            defaults={"content": content, "embedding": embedding},
        )
        logger.info("Embedded defect %s for historical RAG", defect_id)

    except Exception as exc:
        logger.error("embed_defect_task failed for %s: %s", defect_id, exc)
        raise self.retry(exc=exc)
