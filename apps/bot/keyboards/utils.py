from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


def build_grid_keyboard(
    choices: Iterable[tuple],
    callback_factory: Callable,
    columns: int,
    footer: list[InlineKeyboardButton] | None = None,
) -> InlineKeyboardMarkup:
    """Build an inline keyboard grid from (value, label) choices.

    An optional footer row (e.g. a Cancel button) is appended below the grid.
    """
    flat = [
        InlineKeyboardButton(str(label), callback_data=callback_factory(value))
        for value, label in choices
    ]
    rows = [flat[i : i + columns] for i in range(0, len(flat), columns)]
    if footer:
        rows.append(footer)
    return InlineKeyboardMarkup(rows)
