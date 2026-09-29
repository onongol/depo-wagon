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
    return Text("📸 ", _("Receiving the album…"))


def build_photo_too_large_text() -> Text:
    return Text("⚠️ ", _("That photo is too large (max 10 MB) and was not attached."))


def build_edit_photos_text(count: int) -> Text:
    if not count:
        return Text("✏️ ", _("Send a photo of the defect (or skip):"))
    return as_list(
        Text("✏️ ", _("Photos attached:"), " ", count),
        _("Send more photos, clear them, or press Done:"),
        sep="\n\n",
    )


def build_photos_attached_toast(count: int) -> str:
    """Plain text: a callback answer carries no entities."""
    return f"✅ {_('Photos attached:')} {count}"
