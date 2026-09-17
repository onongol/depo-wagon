from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Iterable

    from aiogram.filters.callback_data import CallbackData
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from django.utils.functional import Promise


def build_grid_keyboard(
    buttons: Iterable[tuple[str | Promise, CallbackData]],
    columns: int,
    footer: list[InlineKeyboardButton] | None = None,
) -> InlineKeyboardMarkup:
    """Build an inline keyboard grid from (text, callback data) pairs."""
    builder = InlineKeyboardBuilder()

    for text, callback_data in buttons:
        builder.button(text=str(text), callback_data=callback_data)

    builder.adjust(columns)

    if footer:
        builder.row(*footer)

    return builder.as_markup()
