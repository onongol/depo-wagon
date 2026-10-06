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


# Toasts are plain text: a callback answer carries no entities.
def build_status_changed_toast(status: str) -> str:
    return f"✅ {_('Status changed:')} {status_text(status)}"


def build_status_refused_toast() -> str:
    return f"⚠️ {_('This status change is no longer possible.')}"


def build_status_failed_toast() -> str:
    return f"❌ {_('Failed to update status. Please try again.')}"
