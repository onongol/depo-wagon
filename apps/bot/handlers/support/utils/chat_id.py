import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def support_chat_id() -> int | None:
    """Parsed support chat id, or None if unset or not a valid integer."""
    raw = settings.TELEGRAM_SUPPORT_CHAT_ID
    try:
        return int(raw)
    except TypeError, ValueError:
        if raw:
            logger.warning(
                "Invalid TELEGRAM_SUPPORT_CHAT_ID=%r — support relay disabled.", raw
            )
        return None
