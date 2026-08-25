"""Assembles the support handlers for the bot's dispatcher."""

from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from apps.bot.handlers.common.cancel import cancel
from apps.bot.states import SUPPORT_MESSAGE

from .admin_handlers import support_reply
from .user_handlers import support_receive, support_start
from .utils import support_chat_id


def get_support_handler() -> ConversationHandler:
    """Build the /support relay conversation handler (user → support)."""
    return ConversationHandler(
        entry_points=[CommandHandler("support", support_start)],
        states={
            SUPPORT_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, support_receive)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="support",
        persistent=False,
    )


def get_support_reply_handler() -> MessageHandler | None:
    """Build the handler that routes support replies back to users.

    Returns None if no support chat is configured. Replies to the bot's own
    messages reach the bot even with group privacy mode enabled.
    """
    chat_id = support_chat_id()
    if chat_id is None:
        return None

    return MessageHandler(
        filters.Chat(chat_id=chat_id) & filters.REPLY & ~filters.COMMAND,
        support_reply,
    )
