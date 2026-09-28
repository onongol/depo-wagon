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


def cancel_row() -> list[InlineKeyboardButton]:
    """Bottom row with a Cancel button to exit the conversation from any step."""
    return [InlineKeyboardButton(text=str(BTN_CANCEL), callback_data=CB_CANCEL)]


def with_back_button(keyboard: InlineKeyboardMarkup | None) -> InlineKeyboardMarkup:
    """Back joins a lone bottom button, such as Cancel or Skip, or gets its own row."""
    back = InlineKeyboardButton(text=str(BTN_BACK), callback_data=CB_STEP_BACK)
    rows = [list(row) for row in keyboard.inline_keyboard] if keyboard else []
    if rows and len(rows[-1]) == 1:
        rows[-1].insert(0, back)
    else:
        rows.append([back])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
