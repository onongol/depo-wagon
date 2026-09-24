from aiogram.utils.formatting import (
    Bold,
    Italic,
    Text,
    Url,
    as_key_value,
    as_list,
)
from django.utils.translation import gettext_lazy as _

from .text_connect_page import CONNECT_TELEGRAM, GET_NEW_LINK

_SELECT_ACTION = Bold(_("Select an action below"))


def build_welcome_text(employee) -> Text:
    return as_list(
        Text("👋 ", _("Hello"), ", ", Bold(employee.full_name), "!"),
        Text("👷 ", as_key_value(_("Role"), employee.get_role_display())),
        Text("👇 ", _SELECT_ACTION, ":"),
        sep="\n\n",
    )


_NOT_CONNECTED = _("This chat is not connected to an account yet.")
_NOT_CONNECTED_SIGN_IN = _("Sign in to the web app and press")


def build_not_connected_text(site_url: str) -> Text:
    return as_list(
        Text("👋 ", Bold(_("Welcome!"))),
        _NOT_CONNECTED,
        as_list(
            Text(_NOT_CONNECTED_SIGN_IN, " ", CONNECT_TELEGRAM, ":"),
            Url(site_url),
        ),
        sep="\n\n",
    )


_LINK_CONFIRM = _("Connect this Telegram to")
_LINK_CONFIRM_NOTE = _(
    "The link has been used up either way — declining just means asking "
    "the web app for a new one."
)


def build_link_confirm_text(employee) -> Text:
    return as_list(
        Text("🔗 ", _LINK_CONFIRM, " ", Bold(employee.full_name), "?"),
        Italic(_LINK_CONFIRM_NOTE),
        sep="\n\n",
    )


_LINK_OK = _("Telegram connected!")


def build_link_ok_text() -> Text:
    return Text("✅ ", Bold(_LINK_OK))


_LINK_CANCELLED = _("Cancelled. Nothing was connected.")


def build_link_cancelled_text() -> Text:
    return as_list(_LINK_CANCELLED, GET_NEW_LINK)
