from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _

_NOT_REGISTERED = _("Please register first using /start.")


def build_not_registered_text() -> Text:
    return Text("⚠️ ", _NOT_REGISTERED)
