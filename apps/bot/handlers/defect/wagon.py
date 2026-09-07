import html
import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import (
    BTN_HELP,
    BTN_NEW_DEFECT,
    BTN_OPEN_DEFECTS,
    UD_DEFECT,
    UD_EDITING,
)
from apps.bot.keyboards.defect import department_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DEPARTMENT, WAGON_NUM

from .summary import show_summary

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

    from apps.bot.user_data import DefectData

logger = logging.getLogger(__name__)

MENU_BUTTONS = {str(BTN_NEW_DEFECT), str(BTN_OPEN_DEFECTS), str(BTN_HELP)}


async def receive_wagon_number(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle incoming wagon number text or menu buttons."""
    number = update.message.text.strip()

    if number in MENU_BUTTONS:
        await update.message.reply_text(
            str(M.WAGON_NUM_PROMPT),
            parse_mode=M.PARSE_MODE,
        )
        return WAGON_NUM

    try:
        wagon = await services.get_wagon_by_number(number)
    except Exception:
        logger.exception("Failed to fetch wagon by number %r", number)
        await update.message.reply_text(str(M.SESSION_ERROR))
        return WAGON_NUM

    if not wagon:
        await update.message.reply_text(
            str(M.WAGON_NOT_FOUND).format(number=html.escape(number)),
            parse_mode=M.PARSE_MODE,
        )
        return WAGON_NUM

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.wagon_id = wagon.id
    defect.wagon_number = wagon.number

    if context.user_data.get(UD_EDITING):
        return await show_summary(update, context, defect)

    await update.message.reply_text(
        str(M.WAGON_CONFIRMED).format(number=wagon.number),
        parse_mode=M.PARSE_MODE,
        reply_markup=department_keyboard(),
    )
    return DEPARTMENT
