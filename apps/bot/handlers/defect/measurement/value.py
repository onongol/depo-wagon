from typing import TYPE_CHECKING

from apps.bot.callbacks import NormSkipCB
from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import MEASUREMENT_NORM, MEASUREMENT_VALUE

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

    from apps.bot.user_data import DefectData


async def receive_measurement_value(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receive measurement value as text, validate and save."""
    text = update.message.text.strip()

    try:
        value = float(text.replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            str(M.VALUE_INVALID),
            parse_mode=M.PARSE_MODE,
        )
        return MEASUREMENT_VALUE

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.current_measurement.value = value

    await update.message.reply_text(
        str(M.ASK_NORM),
        reply_markup=skip_keyboard(NormSkipCB()),
    )
    return MEASUREMENT_NORM
