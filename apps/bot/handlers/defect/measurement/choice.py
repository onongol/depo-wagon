from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_DESC_SKIP
from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import dimension_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DESC, MEASUREMENT_DIMENSION
from apps.bot.user_data import DefectData, MeasurementEntry

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


async def measurement_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start a new measurement entry."""
    query = update.callback_query
    await query.answer()

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.current_measurement = MeasurementEntry()

    await query.edit_message_text(
        str(M.ASK_DIMENSION),
        reply_markup=dimension_keyboard(),
    )
    return MEASUREMENT_DIMENSION


async def measurement_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Leave the measurement sub-flow and ask for the description."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        str(M.ASK_DESCRIPTION),
        reply_markup=skip_keyboard(CB_DESC_SKIP),
    )
    return DESC
