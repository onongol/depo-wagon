from typing import TYPE_CHECKING

from apps.bot.callbacks import PhotoSkipCB
from apps.bot.constants import SEVERITY_LABELS, UD_DEFECT, UD_EDITING
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import PHOTO

from .summary import show_summary

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

    from apps.bot.user_data import DefectData


async def receive_severity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming severity selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    sev_value = query.data.value
    sev_label = SEVERITY_LABELS.get(sev_value, sev_value)

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.severity = sev_value
    defect.severity_label = sev_label

    if context.user_data.get(UD_EDITING):
        return await show_summary(update, context, defect)

    await query.edit_message_text(
        str(M.SEVERITY_CONFIRMED).format(label=sev_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(PhotoSkipCB()),
    )
    return PHOTO
