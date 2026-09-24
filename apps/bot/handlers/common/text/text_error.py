from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _


def build_session_error_text() -> Text:
    return Text(
        "⚠️ ", _("Something went wrong. Try again, or send /cancel to start over.")
    )
