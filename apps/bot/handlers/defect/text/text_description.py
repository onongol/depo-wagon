from aiogram.utils.formatting import Text, as_list
from django.utils.translation import gettext_lazy as _

_TOO_LONG = _("Description is too long ({length}/{max} characters).")


def build_ask_description_text() -> Text:
    return Text("📝 ", _("Enter a description of the defect (or skip):"))


def build_edit_description_text() -> Text:
    return Text("✏️ ", _("Enter the description (or skip):"))


def build_description_too_long_text(length: int, limit: int) -> Text:
    return as_list(
        Text("❌ ", str(_TOO_LONG).format(length=length, max=limit)),
        _("Please shorten it:"),
        sep="\n\n",
    )
