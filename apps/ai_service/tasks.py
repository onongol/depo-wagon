import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="ai_service.process_document",
)
def process_document_task(self, document_id: int) -> None:
    """Extract text, embed and store chunks for a DepotDocument."""
    from apps.ai_service.processing.pipeline import process_document

    try:
        process_document(document_id)
    except Exception as exc:
        logger.error(
            "Task failed for document %s (attempt %d/%d): %s",
            document_id,
            self.request.retries + 1,
            self.max_retries + 1,
            exc,
        )
        raise self.retry(exc=exc)
