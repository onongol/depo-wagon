from aiogram.utils.formatting import Text, as_list
from django.utils.translation import gettext_lazy as _

_TOO_LONG = _("Part number is too long ({length}/{max} characters).")


def build_edit_part_number_text() -> Text:
    return Text("✏️ ", _("Enter the part number (or skip):"))


def build_part_number_too_long_text(length: int, limit: int) -> Text:
    return as_list(
        Text("❌ ", str(_TOO_LONG).format(length=length, max=limit)),
        _("Please shorten it (or skip):"),
        sep="\n\n",
    )
