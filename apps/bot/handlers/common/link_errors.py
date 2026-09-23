import logging

from aiogram.utils.formatting import Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.constants import LinkStatus
from apps.bot.messages import BotMessages as M

from .text import GET_NEW_LINK

logger = logging.getLogger(__name__)

_LINK_TOKEN_INVALID = _("This connection link has expired or has already been used.")
_LINK_NO_EMPLOYEE = _(
    "This account is not linked to an active employee record.\n"
    "Please contact your administrator."
)
_LINK_ALREADY_TAKEN = _(
    "This Telegram account is already connected to another employee.\n"
    "Disconnect it there first, or contact your administrator."
)
_LINK_CONFIRM_EXPIRED = _(
    "This confirmation is no longer valid — it expired or has already been answered."
)

_STATUS_MESSAGES = {
    LinkStatus.INVALID_TOKEN: as_list(
        Text("⚠️ ", _LINK_TOKEN_INVALID), GET_NEW_LINK, sep="\n\n"
    ),
    LinkStatus.NO_EMPLOYEE: Text("⚠️ ", _LINK_NO_EMPLOYEE),
    LinkStatus.ALREADY_LINKED: Text("⚠️ ", _LINK_ALREADY_TAKEN),
    LinkStatus.OFFER_EXPIRED: as_list(
        Text("⚠️ ", _LINK_CONFIRM_EXPIRED), GET_NEW_LINK, sep="\n\n"
    ),
}


def get_link_error_message(status: LinkStatus) -> Text:
    """Never leave the chat without an answer, and say so in the log."""
    message = _STATUS_MESSAGES.get(status)
    if message is None:
        logger.error("Link status %s has no message", status)
        return Text(M.SESSION_ERROR)
    return message
