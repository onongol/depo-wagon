import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="core.send_queued_email",
)
def send_queued_email(self, payload: dict) -> None:
    from apps.core.mail import deliver, deserialize_message

    try:
        deliver([deserialize_message(payload)])
    except Exception as exc:  # noqa: BLE001 — any failure must reach retry
        logger.error("Queued mail to %s failed: %s", payload.get("to"), exc)
        raise self.retry(exc=exc)
