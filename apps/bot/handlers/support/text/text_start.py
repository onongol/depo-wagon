from aiogram.utils.formatting import Italic, Text, as_list
from django.utils.translation import gettext_lazy as _


def build_support_ask_text() -> Text:
    return as_list(
        Text("✍️ ", _("Write your question and I'll forward it to the support team.")),
        Italic(_("To exit, type /cancel.")),
    )


def build_support_unavailable_text() -> Text:
    return Text(
        "⚠️ ",
        _("Support is unavailable right now. Please contact @Erdenebayaraa directly."),
    )
