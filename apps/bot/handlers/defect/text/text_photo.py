from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _

_SEND_PHOTO = _("Send a photo of the defect (or skip):")


def build_ask_photo_text() -> Text:
    return Text("📸 ", _SEND_PHOTO)


def build_ask_more_photos_text() -> Text:
    return Text("📸 ", _("Send another photo or press Done:"))


def build_edit_photos_text(*, any_attached: bool) -> Text:
    if not any_attached:
        return Text("✏️ ", _SEND_PHOTO)
    return Text("✏️ ", _("Send more photos, clear them, or press Done:"))


def build_album_receiving_text() -> Text:
    return Text("📸 ", _("Receiving the album…"))


def build_photo_too_large_text() -> Text:
    return Text("⚠️ ", _("That photo is too large (max 10 MB) and was not attached."))


def build_photos_attached_toast(count: int) -> str:
    """Plain text: a callback answer carries no entities."""
    return f"✅ {_('Photos attached:')} {count}"
