from aiogram.utils.formatting import Bold, Text
from django.utils.translation import gettext_lazy as _


def build_support_reply_header() -> Text:
    return Text("💬 ", Bold(_("Reply from support:")))


def build_support_reply_delivered_text() -> Text:
    return Text("✅ ", _("Delivered to the user."))


def build_support_reply_blocked_text() -> Text:
    return Text("⚠️ ", _("Couldn't deliver — the user has blocked the bot."))


def build_support_reply_retry_text() -> Text:
    return Text("⚠️ ", _("Couldn't deliver the reply. Try sending it again."))


def build_support_request_unknown_text() -> Text:
    return Text(
        "⚠️ ",
        _(
            "I can't tell who this answers. Reply to the request message itself, "
            "or the request has expired."
        ),
    )
