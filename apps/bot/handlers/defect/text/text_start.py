from aiogram.utils.formatting import Bold, Italic, Text, as_list
from django.utils.translation import gettext_lazy as _


def build_new_defect_text() -> Text:
    return as_list(
        Text("🔍 ", Bold(_("New Defect Registration"))),
        as_list(_("Enter the wagon number:"), Italic(_("(e.g. 80035668)"))),
        sep="\n\n",
    )
