from typing import TYPE_CHECKING

from apps.bot.fsm import load_defect, save_defect
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.defects.constants import MeasurementDimension

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import DimensionCB

_DIM_LABELS = dict(MeasurementDimension.choices)


async def receive_dimension(
    callback: CallbackQuery, callback_data: DimensionCB, state: FSMContext
) -> None:
    """Receive selected dimension from inline keyboard."""
    await callback.answer()

    dim_value = callback_data.value
    dim_label = str(_DIM_LABELS.get(dim_value, dim_value))

    defect = await load_defect(state)
    defect.current_measurement.dimension = dim_value
    defect.current_measurement.dimension_label = dim_label
    await save_defect(state, defect)

    await callback.message.edit_text(
        str(M.DIMENSION_CONFIRMED).format(label=dim_label), parse_mode=M.PARSE_MODE
    )
    await state.set_state(DefectSG.measurement_value)
