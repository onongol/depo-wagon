from typing import TYPE_CHECKING

from apps.bot.callbacks import DescSkipCB, MeasurementAddCB
from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import dimension_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DESC, MEASUREMENT_DIMENSION
from apps.bot.user_data import DefectData, MeasurementEntry

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


async def handle_measurement_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle user's choice to add measurement or skip."""
    query = update.callback_query
    await query.answer()

    if not isinstance(query.data, MeasurementAddCB):
        await query.edit_message_text(
            str(M.ASK_DESCRIPTION),
            reply_markup=skip_keyboard(DescSkipCB()),
        )
        return DESC

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.current_measurement = MeasurementEntry()

    await query.edit_message_text(
        str(M.ASK_DIMENSION),
        reply_markup=dimension_keyboard(),
    )
    return MEASUREMENT_DIMENSION
