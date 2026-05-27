import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.messages import BotMessages as M

logger = logging.getLogger(__name__)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any active conversation and clear user data."""
    context.user_data.pop("reg", None)
    context.user_data.pop("defect", None)
    await update.message.reply_text(str(M.CANCELLED), parse_mode=M.PARSE_MODE)
    return ConversationHandler.END
