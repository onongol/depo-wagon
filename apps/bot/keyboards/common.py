from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from apps.bot.callback_data import CB_LINK_CANCEL, LinkConfirmCB
from apps.bot.constants import BTN_DONE, BTN_SKIP
from apps.bot.messages import BotMessages as M


def skip_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Single 'Skip' button carrying an already-packed payload."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=str(BTN_SKIP), callback_data=callback_data)]
        ]
    )


def done_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Single 'Done' button carrying an already-packed payload."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=str(BTN_DONE), callback_data=callback_data)]
        ]
    )


def link_confirm_keyboard(employee_id: int) -> InlineKeyboardMarkup:
    """Confirm or decline attaching this chat to an employee."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=str(M.LINK_CONFIRM_BUTTON),
                    callback_data=LinkConfirmCB(employee_id=employee_id).pack(),
                ),
                InlineKeyboardButton(
                    text=str(M.LINK_CANCEL_BUTTON), callback_data=CB_LINK_CANCEL
                ),
            ]
        ]
    )
