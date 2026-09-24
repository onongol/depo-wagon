import logging
from typing import TYPE_CHECKING

from apps.bot.errors import build_session_error_text

from .text import STATUS_MESSAGES

if TYPE_CHECKING:
    from aiogram.utils.formatting import Text

    from apps.bot.constants import LinkStatus

logger = logging.getLogger(__name__)


def get_link_error_message(status: LinkStatus) -> Text:
    """Never leave the chat without an answer, and say so in the log."""
    message = STATUS_MESSAGES.get(status)
    if message is None:
        logger.error("Link status %s has no message", status)
        return build_session_error_text()
    return message
