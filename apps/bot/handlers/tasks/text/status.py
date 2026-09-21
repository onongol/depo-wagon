from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _

from .card import build_card_text
from .utils import status_text, wagon_and_node


def build_status_pick_text(card) -> Text:
    return as_list(
        build_card_text(card),
        Text("⚙️ ", Bold(_("Choose the new status:"))),
        sep="\n\n",
    )


def build_status_confirm_text(defect, target: str) -> Text:
    return as_list(
        Bold(_("Change the status?")),
        Text("🚃 ", wagon_and_node(defect)),
        f"{status_text(defect.status)} → {status_text(target)}",
        sep="\n\n",
    )
