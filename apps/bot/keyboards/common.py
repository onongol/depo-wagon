from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import (
    CB_CANCEL,
    CB_LINK_CANCEL,
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


def back_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text=str(BTN_BACK), callback_data=CB_STEP_BACK)


def cancel_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text=str(BTN_CANCEL), callback_data=CB_CANCEL)


def with_step_buttons(
    keyboard: InlineKeyboardMarkup | None, *, back: bool
) -> InlineKeyboardMarkup:
    """Under the step's own buttons: Back where it leads somewhere, then Cancel."""
    rows = list(keyboard.inline_keyboard) if keyboard else []
    if back:
        rows.append([back_button()])
    return InlineKeyboardMarkup(inline_keyboard=[*rows, [cancel_button()]])


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
