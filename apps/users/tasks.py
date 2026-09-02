import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="users.send_telegram_link_notification",
)
def send_telegram_link_notification(self, user_id: int, action: str) -> None:
    from django.contrib.auth import get_user_model

    from apps.users.notifications import send_telegram_link_email

    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        logger.warning(
            "User %s is gone, dropping the telegram %s notice", user_id, action
        )
        return

    try:
        send_telegram_link_email(user, action)
    except Exception as exc:
        logger.error("telegram %s notice failed for user %s: %s", action, user_id, exc)
        raise self.retry(exc=exc)
