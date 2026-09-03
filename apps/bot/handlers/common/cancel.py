from typing import TYPE_CHECKING

from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from telegram import Update


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any active conversation and clear user data."""
    context.user_data.clear()

    if update.message:
        await update.message.reply_text(str(M.CANCELLED), parse_mode=M.PARSE_MODE)
    elif update.callback_query:
        await update.callback_query.answer(str(M.CANCELLED))
    return ConversationHandler.END
