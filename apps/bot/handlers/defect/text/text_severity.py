from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _

_SELECT_SEVERITY = _("Select severity:")


def build_ask_severity_text() -> Text:
    return Text("🌡️ ", _SELECT_SEVERITY)


def build_edit_severity_text() -> Text:
    return Text("✏️ ", _SELECT_SEVERITY)
