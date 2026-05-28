import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.constants import UD_DEFECT
from apps.bot.user_data import DefectData
from apps.bot.keyboards.defect import severity_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import SEVERITY

logger = logging.getLogger(__name__)


async def receive_defect_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle incoming defect type selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    dtype_value = query.data.value

    from apps.defects.constants import DefectType

    dtype_label = dict(DefectType.choices).get(dtype_value, dtype_value)

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.defect_type = dtype_value
    defect.defect_type_label = dtype_label

    await query.edit_message_text(
        str(M.DEFECT_TYPE_CONFIRMED).format(label=dtype_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=severity_keyboard(),
    )
    return SEVERITY
