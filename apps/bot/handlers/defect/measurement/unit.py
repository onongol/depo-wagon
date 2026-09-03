from typing import TYPE_CHECKING

from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.defect import measurement_next_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import MEASUREMENT_CHOICE

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

    from apps.bot.user_data import DefectData


def _save_measurement(defect: DefectData) -> str:
    current = defect.current_measurement
    defect.measurements.append(current)
    defect.current_measurement = None
    unit = f" {current.unit}" if current.unit else ""

    return str(M.MEASUREMENT_SAVED).format(
        count=len(defect.measurements),
        label=current.dimension_label,
        value=current.value,
        unit=unit,
    )


async def receive_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive unit as text."""
    defect: DefectData = context.user_data[UD_DEFECT]
    defect.current_measurement.unit = update.message.text.strip()

    await update.message.reply_text(
        _save_measurement(defect),
        parse_mode=M.PARSE_MODE,
        reply_markup=measurement_next_keyboard(),
    )
    return MEASUREMENT_CHOICE


async def skip_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip unit."""
    query = update.callback_query
    await query.answer()

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.current_measurement.unit = ""

    await query.edit_message_text(
        _save_measurement(defect),
        parse_mode=M.PARSE_MODE,
        reply_markup=measurement_next_keyboard(),
    )
    return MEASUREMENT_CHOICE
