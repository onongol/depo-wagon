from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _


def build_ask_department_text() -> Text:
    return Text("🏭 ", _("Select the department:"))
