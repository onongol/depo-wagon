from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import (
    CB_DESC_SKIP,
    CB_LINK_CANCEL,
    CB_MEAS_CLEAR,
    CB_MEAS_DONE,
    CB_MEAS_SKIP,
    CB_PART_NUMBER_SKIP,
    CB_PHOTO_CLEAR,
    CB_PHOTO_SKIP,
    CB_RESP_EMP_SKIP,
    CB_STEP_BACK,
    LinkConfirmCB,
)
from apps.bot.constants import (
    BTN_BACK,
    BTN_CANCEL,
    BTN_CLEAR,
    BTN_CONNECT,
    BTN_DONE,
    BTN_SKIP,
)

# A step's own way on, and Clear: under Back, which comes first
_UNDER_BACK = frozenset(
    {
        CB_DESC_SKIP,
        CB_MEAS_CLEAR,
        CB_MEAS_DONE,
        CB_MEAS_SKIP,
        CB_PART_NUMBER_SKIP,
        CB_PHOTO_CLEAR,
        CB_PHOTO_SKIP,
        CB_RESP_EMP_SKIP,
    }
)


def with_back_button(keyboard: InlineKeyboardMarkup | None) -> InlineKeyboardMarkup:
    """Back on a row of its own, under the step's choices and above its Skip."""
    back = [InlineKeyboardButton(text=str(BTN_BACK), callback_data=CB_STEP_BACK)]
    rows = list(keyboard.inline_keyboard) if keyboard else []
    at = len(rows)
    while at and all(button.callback_data in _UNDER_BACK for button in rows[at - 1]):
        at -= 1
    return InlineKeyboardMarkup(inline_keyboard=[*rows[:at], back, *rows[at:]])


def skip_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Single 'Skip' button carrying an already-packed payload."""
    builder = InlineKeyboardBuilder()
    builder.button(text=str(BTN_SKIP), callback_data=callback_data)
    return builder.as_markup()


def done_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Single 'Done' button carrying an already-packed payload."""
    builder = InlineKeyboardBuilder()
    builder.button(text=str(BTN_DONE), callback_data=callback_data)
    return builder.as_markup()


def clear_or_done_keyboard(clear: str, done: str) -> InlineKeyboardMarkup:
    """Drop what an Edit reopened, or keep it and go back."""
    builder = InlineKeyboardBuilder()
    builder.button(text=str(BTN_CLEAR), callback_data=clear)
    builder.button(text=str(BTN_DONE), callback_data=done)
    builder.adjust(1)
    return builder.as_markup()


def link_confirm_keyboard(employee_id: int) -> InlineKeyboardMarkup:
    """Confirm or decline attaching this chat to an employee."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=str(BTN_CONNECT),
        callback_data=LinkConfirmCB(employee_id=employee_id),
    )
    builder.button(text=str(BTN_CANCEL), callback_data=CB_LINK_CANCEL)
    return builder.as_markup()
