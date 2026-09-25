from aiogram.utils.formatting import Bold, Code, Italic, Text, as_list
from django.utils.translation import gettext_lazy as _


def build_ask_wagon_text() -> Text:
    return as_list(
        as_list(
            Text("⬆️ ", _("Please enter the wagon number:")),
            Italic(_("(e.g. 80035668)")),
        ),
        _("To exit, type /cancel."),
        sep="\n\n",
    )


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
