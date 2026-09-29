from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _

_ENTER_PART_NUMBER = _("Enter the part number (or skip):")
_TOO_LONG = _("Part number is too long ({length}/{max} characters).")


def build_ask_part_number_text() -> Text:
    return Text("🔢 ", _ENTER_PART_NUMBER)


def build_edit_part_number_text() -> Text:
    return Text("✏️ ", _ENTER_PART_NUMBER)


def build_part_number_too_long_text(length: int, limit: int) -> Text:
    return Text("❌ ", str(_TOO_LONG).format(length=length, max=limit))
