"""Callback-query filters."""

from typing import TYPE_CHECKING

from aiogram.filters import BaseFilter

from apps.bot.callback_data import is_known_callback

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery


class KnownCallback(BaseFilter):
    """Whether this build can still parse the payload.

    Separates a tap that arrived in the wrong state — absorb it quietly — from
    one this build cannot make sense of at all, which the user is told about.
    """

    async def __call__(self, callback: CallbackQuery) -> bool:
        return bool(callback.data) and is_known_callback(callback.data)
