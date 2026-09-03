import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    # OCR is one network call per page, so the global limit is far too tight here.
    soft_time_limit=1800,
    time_limit=1860,
    name="ai_service.process_document",
)
def process_document_task(self, document_id: int) -> None:
    from apps.ai_service.processing.pipeline import process_document

    try:
        process_document(document_id)
    except Exception as exc:  # noqa: BLE001 — any failure must reach retry
        logger.error(
            "Task failed for document %s (attempt %d/%d): %s",
            document_id,
            self.request.retries + 1,
            self.max_retries + 1,
            exc,
        )
        raise self.retry(exc=exc)
