from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from apps.bot.callbacks import LinkCancelCB, LinkConfirmCB
from apps.bot.constants import BTN_SKIP
from apps.bot.messages import BotMessages as M


def skip_keyboard(callback_data) -> InlineKeyboardMarkup:
    """Single 'Skip' button with any typed callback."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(str(BTN_SKIP), callback_data=callback_data)]]
    )


def link_confirm_keyboard(employee_id: int) -> InlineKeyboardMarkup:
    """Confirm or decline attaching this chat to an employee."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    str(M.LINK_CONFIRM_BUTTON),
                    callback_data=LinkConfirmCB(employee_id=employee_id),
                ),
                InlineKeyboardButton(
                    str(M.LINK_CANCEL_BUTTON), callback_data=LinkCancelCB()
                ),
            ]
        ]
    )
