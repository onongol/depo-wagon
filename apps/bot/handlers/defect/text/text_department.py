from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _


def build_department_confirmed_text(label: str) -> Text:
    return as_list(
        Text("✅ ", _("Department:"), " ", Bold(label)),
        _("Select the defect node:"),
        sep="\n\n",
    )
