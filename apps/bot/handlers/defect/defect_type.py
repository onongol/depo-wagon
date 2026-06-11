from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.constants import UD_DEFECT, UD_EDITING
from apps.bot.keyboards.defect import severity_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import SEVERITY
from apps.bot.user_data import DefectData
from apps.defects.constants import DefectType

from .summary import show_summary

_DEFECT_TYPE_LABELS = dict(DefectType.choices)


async def receive_defect_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle incoming defect type selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    dtype_value = query.data.value
    dtype_label = _DEFECT_TYPE_LABELS.get(dtype_value, dtype_value)

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.defect_type = dtype_value
    defect.defect_type_label = dtype_label

    if context.user_data.get(UD_EDITING):
        return await show_summary(update, context, defect)

    await query.edit_message_text(
        str(M.DEFECT_TYPE_CONFIRMED).format(label=dtype_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=severity_keyboard(),
    )
    return SEVERITY
