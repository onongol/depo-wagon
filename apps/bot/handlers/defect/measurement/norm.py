from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.callbacks import NormSkipCB, UnitSkipCB
from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import MEASUREMENT_NORM, MEASUREMENT_UNIT
from apps.bot.user_data import DefectData


async def receive_norm_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive norm value as text."""
    defect: DefectData = context.user_data[UD_DEFECT]
    text = update.message.text.strip()

    try:
        norm = float(text.replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            str(M.NORM_INVALID),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard(NormSkipCB()),
        )
        return MEASUREMENT_NORM

    defect.current_measurement.norm_value = norm

    await update.message.reply_text(
        str(M.ASK_UNIT),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(UnitSkipCB()),
    )
    return MEASUREMENT_UNIT


async def skip_norm_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip norm value."""
    query = update.callback_query
    await query.answer()

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.current_measurement.norm_value = None

    await query.edit_message_text(
        str(M.ASK_UNIT),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(UnitSkipCB()),
    )
    return MEASUREMENT_UNIT
