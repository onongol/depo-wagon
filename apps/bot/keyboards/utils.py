from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


def build_grid_keyboard(
    choices: Iterable[tuple],
    callback_factory: Callable,
    columns: int,
    footer: list[InlineKeyboardButton] | None = None,
) -> InlineKeyboardMarkup:
    """Build an inline keyboard grid from (value, label) choices.

    Every factory passed here names its field `value`, so the call sites need
    no lambda. An optional footer row (e.g. Cancel) is appended below the grid.
    """
    flat = [
        InlineKeyboardButton(
            text=str(label), callback_data=callback_factory(value=value).pack()
        )
        for value, label in choices
    ]
    rows = [flat[i : i + columns] for i in range(0, len(flat), columns)]
    if footer:
        rows.append(footer)
    return InlineKeyboardMarkup(inline_keyboard=rows)
