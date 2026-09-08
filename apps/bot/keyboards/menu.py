from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from apps.bot.constants import BTN_ASK, BTN_HELP, BTN_NEW_DEFECT, BTN_OPEN_DEFECTS
from apps.core.constants.constants import EmployeeRole

_ROLES_WITH_TASKS = {
    EmployeeRole.INSPECTOR,
    EmployeeRole.MASTER,
    EmployeeRole.ENGINEER,
    EmployeeRole.MANAGER,
}


def main_menu_keyboard(role: str) -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text=str(BTN_NEW_DEFECT))]]

    if role in _ROLES_WITH_TASKS:
        buttons.append([KeyboardButton(text=str(BTN_OPEN_DEFECTS))])

    buttons.append([KeyboardButton(text=str(BTN_ASK))])
    buttons.append([KeyboardButton(text=str(BTN_HELP))])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
