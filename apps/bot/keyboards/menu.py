from typing import TYPE_CHECKING

from aiogram.utils.keyboard import ReplyKeyboardBuilder

from apps.bot.constants import BTN_ASK, BTN_HELP, BTN_NEW_DEFECT, BTN_OPEN_DEFECTS

if TYPE_CHECKING:
    from aiogram.types import ReplyKeyboardMarkup

_MENU_BUTTONS = (BTN_NEW_DEFECT, BTN_OPEN_DEFECTS, BTN_ASK, BTN_HELP)

MENU_TEXTS = frozenset(str(button) for button in _MENU_BUTTONS)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for button in _MENU_BUTTONS:
        builder.button(text=str(button))

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
