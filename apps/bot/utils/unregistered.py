from typing import TYPE_CHECKING

from aiogram.types import Message
from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _

from apps.bot.utils.screens import edit_or_send

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery

_NOT_REGISTERED = _("Please register first using /start.")


def build_not_registered_text() -> Text:
    return Text("⚠️ ", _NOT_REGISTERED)


async def refuse_unregistered(event: Message | CallbackQuery) -> None:
    """A chat with no employee behind it; a tapped button's message is replaced."""
    if isinstance(event, Message):
        await event.answer(**build_not_registered_text().as_kwargs())
        return

    await event.answer()
    await edit_or_send(event, **build_not_registered_text().as_kwargs())
