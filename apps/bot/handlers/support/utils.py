import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Redis key: relayed group message_id -> asking user's chat id.
# TTL caps growth and survives bot restarts (within the window).
SUPPORT_MAP_PREFIX = "support_reply:"
SUPPORT_MAP_TTL = 7 * 24 * 3600  # 7 days


def support_chat_id() -> int | None:
    """Parsed support chat id, or None if unset or not a valid integer."""
    raw = settings.TELEGRAM_SUPPORT_CHAT_ID
    try:
        return int(raw)
    except (TypeError, ValueError):
        if raw:
            logger.warning(
                "Invalid TELEGRAM_SUPPORT_CHAT_ID=%r — support relay disabled.", raw
            )
        return None


def _map_key(message_id: int) -> str:
    return f"{SUPPORT_MAP_PREFIX}{message_id}"


async def remember_request(message_id: int, user_id: int) -> None:
    """Link a relayed group message to the user who sent the request."""
    await sync_to_async(cache.set)(_map_key(message_id), user_id, timeout=SUPPORT_MAP_TTL)


async def lookup_request(message_id: int) -> int | None:
    """Return the user id behind a relayed message, or None if unknown/expired."""
    return await sync_to_async(cache.get)(_map_key(message_id))
