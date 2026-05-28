import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.constants import UD_DEFECT
from apps.bot.messages import BotMessages as M

logger = logging.getLogger(__name__)


async def cancel_defect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the defect registration conversation."""
    context.user_data.pop(UD_DEFECT, None)
    await update.message.reply_text(str(M.DEFECT_CANCELLED))
    return ConversationHandler.END
