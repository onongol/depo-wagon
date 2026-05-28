from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from apps.bot.constants import BTN_SKIP


def skip_keyboard(callback_data) -> InlineKeyboardMarkup:
    """Single 'Skip' button with any typed callback."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(str(BTN_SKIP), callback_data=callback_data)]]
    )
