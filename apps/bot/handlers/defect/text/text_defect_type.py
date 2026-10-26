from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _

_SELECT_TYPE = _("Select the defect type:")


def build_ask_defect_type_text() -> Text:
    return Text("⚠️ ", _SELECT_TYPE)


def build_edit_defect_type_text() -> Text:
    return Text("✏️ ", _SELECT_TYPE)
