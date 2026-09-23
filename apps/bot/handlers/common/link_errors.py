import logging

from apps.bot.constants import LinkStatus
from apps.bot.messages import BotMessages as M

logger = logging.getLogger(__name__)

_STATUS_MESSAGES = {
    LinkStatus.INVALID_TOKEN: M.LINK_TOKEN_INVALID,
    LinkStatus.NO_EMPLOYEE: M.LINK_NO_EMPLOYEE,
    LinkStatus.ALREADY_LINKED: M.LINK_ALREADY_TAKEN,
    LinkStatus.OFFER_EXPIRED: M.LINK_CONFIRM_EXPIRED,
}


def get_link_error_message(status: LinkStatus):
    """Never leave the chat without an answer, and say so in the log."""
    message = _STATUS_MESSAGES.get(status)
    if message is None:
        logger.error("Link status %s has no message", status)
        return M.SESSION_ERROR
    return message
