from aiogram.utils.formatting import Text, as_list
from django.utils.translation import gettext_lazy as _

_TOO_LONG = _("Description is too long ({length}/{max} characters).")
_SELECT_SEVERITY = _("Select severity:")


def build_ask_description_text() -> Text:
    return Text("📝 ", _("Enter a description of the defect (or skip):"))


def build_edit_description_text() -> Text:
    return Text("✏️ ", _("Enter the description (or skip):"))


def build_description_too_long_text(length: int, limit: int) -> Text:
    return Text("❌ ", str(_TOO_LONG).format(length=length, max=limit))


def build_description_added_text() -> Text:
    return as_list(Text("✅ ", _("Description added.")), _SELECT_SEVERITY, sep="\n\n")


def build_description_skipped_text() -> Text:
    return as_list(Text("⏭ ", _("Description skipped.")), _SELECT_SEVERITY, sep="\n\n")
