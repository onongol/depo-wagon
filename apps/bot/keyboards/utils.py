from typing import Callable, Iterable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_grid_keyboard(
    choices: Iterable[tuple],
    callback_factory: Callable,
    columns: int,
) -> InlineKeyboardMarkup:
    """Build an inline keyboard grid from (value, label) choices."""
    flat = [
        InlineKeyboardButton(str(label), callback_data=callback_factory(value))
        for value, label in choices
    ]
    return InlineKeyboardMarkup(
        [flat[i : i + columns] for i in range(0, len(flat), columns)]
    )
