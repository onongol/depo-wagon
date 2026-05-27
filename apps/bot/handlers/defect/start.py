import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.handlers.employee import get_employee
from apps.bot.messages import BotMessages as M
from apps.bot.states import WAGON_NUM

logger = logging.getLogger(__name__)


async def new_defect_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /new_defect or menu button."""
    employee = await get_employee(update, context)

    if not employee:
        await update.message.reply_text(str(M.NOT_REGISTERED))
        return ConversationHandler.END

    context.user_data["defect"] = {}

    await update.message.reply_text(
        str(M.NEW_DEFECT_START),
        parse_mode=M.PARSE_MODE,
    )
    return WAGON_NUM
