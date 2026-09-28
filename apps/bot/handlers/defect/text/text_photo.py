from aiogram.utils.formatting import Text, as_list
from django.utils.translation import gettext_lazy as _

_PHOTO_RECEIVED = _("Photo {count} received.")


def build_photo_received_text(count: int) -> Text:
    return as_list(
        Text("✅ ", str(_PHOTO_RECEIVED).format(count=count)),
        Text("📸 ", _("Send another photo or press Done:")),
        sep="\n\n",
    )


def build_album_receiving_text() -> Text:
    return as_list(
        Text("📸 ", _("Receiving the album.")),
        _("Send more photos or press Done when finished:"),
        sep="\n\n",
    )


def build_photo_too_large_text() -> Text:
    return Text("⚠️ ", _("Photo is too large (max 10 MB). Please send a smaller photo:"))


def build_photos_attached_toast(count: int) -> str:
    """Plain text: a callback answer carries no entities."""
    return f"✅ {_('Photos attached:')} {count}"
