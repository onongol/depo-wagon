from aiogram.utils.formatting import Bold, Text
from django.utils.translation import gettext_lazy as _


def build_new_defect_text() -> Text:
    return Text("🔍 ", Bold(_("New Defect Registration")))
