from aiogram.utils.formatting import Code, Italic, Text, as_list
from django.utils.translation import gettext_lazy as _


def build_ask_wagon_text() -> Text:
    return as_list(
        Text("🚃 ", _("Enter the wagon number:")), Italic(_("(e.g. 80035668)"))
    )


def build_edit_wagon_text() -> Text:
    return Text("✏️ ", _("Enter the new wagon number:"))


def build_wagon_not_found_text(number: str) -> Text:
    return Text("❌ ", _("Wagon not found:"), " ", Code(number))
