from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import CB_CANCEL, CB_LINK_CANCEL, LinkConfirmCB
from apps.bot.constants import BTN_CANCEL, BTN_DONE, BTN_SKIP
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup


def cancel_row() -> list[InlineKeyboardButton]:
    """Bottom row with a Cancel button to exit the conversation from any step."""
    return [InlineKeyboardButton(text=str(BTN_CANCEL), callback_data=CB_CANCEL)]


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


def link_confirm_keyboard(employee_id: int) -> InlineKeyboardMarkup:
    """Confirm or decline attaching this chat to an employee."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=str(M.LINK_CONFIRM_BUTTON),
        callback_data=LinkConfirmCB(employee_id=employee_id),
    )
    builder.button(text=str(M.LINK_CANCEL_BUTTON), callback_data=CB_LINK_CANCEL)
    return builder.as_markup()
