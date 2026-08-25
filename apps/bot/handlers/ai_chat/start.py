import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.constants import UD_AI_CHAT_HISTORY
from apps.bot.handlers.employee import get_employee
from apps.bot.messages import BotMessages as M
from apps.bot.states import AI_CHAT

logger = logging.getLogger(__name__)


async def ai_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        employee = await get_employee(update, context)
    except Exception:
        logger.exception(
            "Failed to fetch employee for user %s", update.effective_user.id
        )
        return ConversationHandler.END

    if not employee:
        try:
            await update.message.reply_text(str(M.AI_CHAT_NOT_AUTHENTICATED))
        except Exception:
            pass
        return ConversationHandler.END

    context.user_data[UD_AI_CHAT_HISTORY] = []

    try:
        await update.message.reply_text(
            str(M.AI_CHAT_GREETING),
            parse_mode=M.PARSE_MODE,
        )
    except Exception:
        logger.warning("Could not send greeting for user %s", update.effective_user.id)
        return ConversationHandler.END

    return AI_CHAT
