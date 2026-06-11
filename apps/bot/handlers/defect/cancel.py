from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.constants import DEFECT_USER_DATA_KEYS
from apps.bot.messages import BotMessages as M


async def cancel_defect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the defect registration conversation (text command or inline button)."""
    for key in DEFECT_USER_DATA_KEYS:
        context.user_data.pop(key, None)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(str(M.DEFECT_CANCELLED))
    else:
        await update.message.reply_text(str(M.DEFECT_CANCELLED))
    return ConversationHandler.END


async def stale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Silently dismiss stale inline keyboard callbacks from previous steps."""
    await update.callback_query.answer()
