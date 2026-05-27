import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.keyboards import severity_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import SEVERITY

logger = logging.getLogger(__name__)


async def receive_defect_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    dtype_value = query.data.split(":", 1)[1]
    context.user_data["defect"]["defect_type"] = dtype_value

    from apps.defects.constants import DefectType

    dtype_label = dict(DefectType.choices).get(dtype_value, dtype_value)
    context.user_data["defect"]["defect_type_label"] = dtype_label

    await query.edit_message_text(
        str(M.DEFECT_TYPE_CONFIRMED).format(label=dtype_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=severity_keyboard(),
    )
    return SEVERITY
