from aiogram.utils.formatting import Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.constants import LinkStatus

from .text_connect_page import GET_NEW_LINK

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

STATUS_MESSAGES = {
    LinkStatus.INVALID_TOKEN: as_list(
        Text("⚠️ ", _LINK_TOKEN_INVALID), GET_NEW_LINK, sep="\n\n"
    ),
    LinkStatus.NO_EMPLOYEE: Text("⚠️ ", _LINK_NO_EMPLOYEE),
    LinkStatus.ALREADY_LINKED: Text("⚠️ ", _LINK_ALREADY_TAKEN),
    LinkStatus.OFFER_EXPIRED: as_list(
        Text("⚠️ ", _LINK_CONFIRM_EXPIRED), GET_NEW_LINK, sep="\n\n"
    ),
}
