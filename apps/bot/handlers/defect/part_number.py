import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.constants import UD_DEFECT
from apps.bot.user_data import DefectData
from apps.bot.keyboards.defect import defect_type_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DEFECT_TYPE

logger = logging.getLogger(__name__)


async def receive_part_number(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle part number text input or skip."""
    defect: DefectData = context.user_data[UD_DEFECT]

    if update.callback_query:
        await update.callback_query.answer()
        defect.part_number = ""
        await update.callback_query.edit_message_text(
            str(M.PART_NUMBER_SKIPPED),
            parse_mode=M.PARSE_MODE,
            reply_markup=defect_type_keyboard(),
        )
    else:
        part_number = update.message.text.strip()
        defect.part_number = part_number
        await update.message.reply_text(
            str(M.PART_NUMBER_CONFIRMED).format(part_number=part_number),
            parse_mode=M.PARSE_MODE,
            reply_markup=defect_type_keyboard(),
        )

    return DEFECT_TYPE
