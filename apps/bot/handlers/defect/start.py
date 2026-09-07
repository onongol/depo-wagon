import logging
from typing import TYPE_CHECKING

from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.constants import UD_DEFECT
from apps.bot.handlers.employee import get_employee
from apps.bot.messages import BotMessages as M
from apps.bot.states import WAGON_NUM
from apps.bot.user_data import DefectData

if TYPE_CHECKING:
    from telegram import Update

logger = logging.getLogger(__name__)


async def new_defect_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /new_defect or menu button."""
    try:
        employee = await get_employee(update, context)
    except Exception:
        logger.exception("Failed to fetch employee in new_defect_start")
        await update.message.reply_text(str(M.SESSION_ERROR))
        return ConversationHandler.END

    if not employee:
        await update.message.reply_text(str(M.NOT_REGISTERED))
        return ConversationHandler.END

    context.user_data[UD_DEFECT] = DefectData()

    await update.message.reply_text(
        str(M.NEW_DEFECT_START),
        parse_mode=M.PARSE_MODE,
    )
    return WAGON_NUM
