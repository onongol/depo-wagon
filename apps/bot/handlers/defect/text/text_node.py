from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _


def build_ask_node_text() -> Text:
    return Text("🔧 ", _("Select the defect node:"))


def build_edit_node_text() -> Text:
    return Text("✏️ ", _("Select the node:"))
