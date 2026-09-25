from aiogram.utils.formatting import Bold, Code, Text, as_list
from django.utils.translation import gettext_lazy as _


def build_edit_wagon_text() -> Text:
    return Text("✏️ ", _("Enter the new wagon number:"))


def build_wagon_not_found_text(number: str) -> Text:
    return as_list(
        Text("❌ ", _("Wagon not found:"), " ", Code(number)),
        _("Please check and try again:"),
        sep="\n\n",
    )


def build_wagon_confirmed_text(number: str) -> Text:
    return as_list(
        Text("✅ ", _("Wagon:"), " ", Bold(number)),
        _("Select the department:"),
        sep="\n\n",
    )
