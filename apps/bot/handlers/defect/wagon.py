import html
import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot import services
from apps.bot.constants import BTN_HELP, BTN_NEW_DEFECT, BTN_OPEN_DEFECTS
from apps.bot.keyboards import node_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import NODE, WAGON_NUM

logger = logging.getLogger(__name__)

MENU_BUTTONS = {str(BTN_NEW_DEFECT), str(BTN_OPEN_DEFECTS), str(BTN_HELP)}


async def receive_wagon_number(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    number = update.message.text.strip()

    if number in MENU_BUTTONS:
        await update.message.reply_text(
            str(M.WAGON_NUM_PROMPT),
            parse_mode=M.PARSE_MODE,
        )
        return WAGON_NUM

    wagon = await services.get_wagon_by_number(number)

    if not wagon:
        await update.message.reply_text(
            str(M.WAGON_NOT_FOUND).format(number=html.escape(number)),
            parse_mode=M.PARSE_MODE,
        )
        return WAGON_NUM

    context.user_data["defect"]["wagon_id"] = wagon.id
    context.user_data["defect"]["wagon_number"] = wagon.number

    await update.message.reply_text(
        str(M.WAGON_CONFIRMED).format(number=wagon.number),
        parse_mode=M.PARSE_MODE,
        reply_markup=node_keyboard(),
    )
    return NODE
