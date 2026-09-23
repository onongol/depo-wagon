from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _


def build_cancelled_text() -> Text:
    return Text("❌ ", _("Cancelled."))
