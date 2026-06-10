from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.constants import UD_DEFECT
from apps.bot.handlers.defect.photo import UD_LAST_PHOTO_MSG
from apps.bot.handlers.defect.responsible_employee import (
    UD_RESP_EMPLOYEES,
    UD_RESP_SEARCH,
)
from apps.bot.messages import BotMessages as M

_DEFECT_KEYS = (UD_DEFECT, UD_RESP_EMPLOYEES, UD_RESP_SEARCH, UD_LAST_PHOTO_MSG)


async def cancel_defect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the defect registration conversation."""
    for key in _DEFECT_KEYS:
        context.user_data.pop(key, None)
    await update.message.reply_text(str(M.DEFECT_CANCELLED))
    return ConversationHandler.END


async def stale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Silently dismiss stale inline keyboard callbacks from previous steps."""
    await update.callback_query.answer()
