from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters

from apps.bot.constants import (
    BTN_ASK,
    BTN_CANCEL,
    BTN_HELP,
    BTN_NEW_DEFECT,
    BTN_OPEN_DEFECTS,
)
from apps.bot.handlers.common.cancel import cancel
from apps.bot.states import AI_CHAT

from .receive import ai_chat_receive
from .start import ai_chat_start

_MENU_TEXTS = [
    str(BTN_NEW_DEFECT),
    str(BTN_OPEN_DEFECTS),
    str(BTN_HELP),
    str(BTN_CANCEL),
    str(BTN_ASK),
]


def get_ai_chat_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("ask", ai_chat_start),
            MessageHandler(filters.Text(str(BTN_ASK)), ai_chat_start),
        ],
        states={
            AI_CHAT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Text(_MENU_TEXTS),
                    ai_chat_receive,
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Text(_MENU_TEXTS), cancel),
        ],
        name="ai_chat",
        persistent=False,
        conversation_timeout=600,
    )
