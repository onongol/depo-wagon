from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _

_MSG_EXPIRED_BUTTON_TEXT = _(
    "This button is no longer valid — the bot has restarted since it was sent."
)
_MSG_EXPIRED_BUTTON_HINT = _("Send /start to begin again.")


def build_button_expired_text() -> Text:
    return as_list(
        Text(
            "⏳ ",
            _MSG_EXPIRED_BUTTON_TEXT,
        ),
        _MSG_EXPIRED_BUTTON_HINT,
        sep="\n\n",
    )


_MSG_NO_STATE_HEADER = _("There is no step waiting for this message.")
_MSG_NO_STATE_BODY_PREFIX = _("An unfinished form expires after a while — tap")
_MSG_NO_STATE_BODY_SUFFIX = _("or send /help to start again.")


def build_unhandled_message_text() -> Text:
    return as_list(
        Text("⚠️ ", _MSG_NO_STATE_HEADER),
        Text(
            _MSG_NO_STATE_BODY_PREFIX,
            " ",
            Bold(_("Menu")),
            " ",
            _MSG_NO_STATE_BODY_SUFFIX,
        ),
        sep="\n\n",
    )
