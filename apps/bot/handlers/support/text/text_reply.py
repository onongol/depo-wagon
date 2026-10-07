from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _


def build_support_reply_header() -> Text:
    return Text("💬 ", Bold(_("Reply from support:")))


def build_support_reply_text(reply: str) -> Text:
    return as_list(build_support_reply_header(), reply, sep="\n\n")


def build_support_reply_delivered_text() -> Text:
    return Text("✅ ", _("Delivered to the user."))


def build_support_reply_failed_text() -> Text:
    return Text("⚠️ ", _("Couldn't deliver — the user may have blocked the bot."))
