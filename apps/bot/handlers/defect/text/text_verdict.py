from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _

_YOUR_VERDICT = _("Your verdict:")


def build_ask_verdict_text() -> Text:
    return Text("👨‍🔧 ", _YOUR_VERDICT)


def build_edit_verdict_text() -> Text:
    return Text("✏️ ", _YOUR_VERDICT)
