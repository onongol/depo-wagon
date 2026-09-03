from typing import TYPE_CHECKING

from apps.bot.constants import UD_DEFECT
from apps.bot.messages import BotMessages as M
from apps.bot.states import MEASUREMENT_VALUE
from apps.defects.constants import MeasurementDimension

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

    from apps.bot.user_data import DefectData

_DIM_LABELS = dict(MeasurementDimension.choices)


async def receive_dimension(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive selected dimension from inline keyboard."""
    query = update.callback_query
    await query.answer()

    dim_value = query.data.value
    dim_label = _DIM_LABELS.get(dim_value, dim_value)

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.current_measurement.dimension = dim_value
    defect.current_measurement.dimension_label = dim_label

    await query.edit_message_text(
        str(M.DIMENSION_CONFIRMED).format(label=dim_label),
        parse_mode=M.PARSE_MODE,
    )
    return MEASUREMENT_VALUE
