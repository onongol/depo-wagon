from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _


def build_edit_node_text() -> Text:
    return Text("✏️ ", _("Select the node:"))


def build_node_confirmed_text(label: str) -> Text:
    return as_list(
        Text("✅ ", _("Node:"), " ", Bold(label)),
        _("Enter the part number (or skip):"),
        sep="\n\n",
    )
