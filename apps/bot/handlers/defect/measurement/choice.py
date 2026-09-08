from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_DESC_SKIP
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import dimension_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.user_data import MeasurementEntry

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery


async def measurement_add(callback: CallbackQuery, state: FSMContext) -> None:
    """Start a new measurement entry."""
    await callback.answer()

    defect = await load_defect(state)
    defect.current_measurement = MeasurementEntry()
    await save_defect(state, defect)

    await callback.message.edit_text(
        str(M.ASK_DIMENSION), reply_markup=dimension_keyboard()
    )
    await state.set_state(DefectSG.measurement_dimension)


async def measurement_done(callback: CallbackQuery, state: FSMContext) -> None:
    """Leave the measurement sub-flow and ask for the description."""
    await callback.answer()

    await callback.message.edit_text(
        str(M.ASK_DESCRIPTION), reply_markup=skip_keyboard(CB_DESC_SKIP)
    )
    await state.set_state(DefectSG.desc)
