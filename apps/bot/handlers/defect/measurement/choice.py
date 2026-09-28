from typing import TYPE_CHECKING, Any

from aiogram import F
from aiogram.fsm.scene import on

from apps.bot.callback_data import CB_DESC_SKIP, CB_MEAS_ADD, CB_MEAS_DONE, CB_MEAS_SKIP
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.defect.scene import DefectScene
from apps.bot.handlers.defect.text import build_ask_measurement_text
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.measurement import (
    dimension_keyboard,
    measurement_choice_keyboard,
    measurement_next_keyboard,
)
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.user_data import MeasurementEntry

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.handlers.defect.scene import Screen
    from apps.bot.user_data import DefectData


class MeasurementChoiceScene(DefectScene, state=DefectSG.measurement_choice.state):
    """Add one or move on; once there are some, the screen names the last saved."""

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if not form.measurements:
            return build_ask_measurement_text(), measurement_choice_keyboard()

        last = form.measurements[-1]
        text = str(M.MEASUREMENT_SAVED).format(
            count=len(form.measurements),
            label=last.dimension_label,
            value=last.value,
            unit=f" {last.unit}" if last.unit else "",
        )
        return text, measurement_next_keyboard()

    @on.callback_query(F.data == CB_MEAS_ADD)
    async def add(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()

        defect = await load_defect(state)
        defect.current_measurement = MeasurementEntry()
        await save_defect(state, defect)

        await callback.message.edit_text(
            str(M.ASK_DIMENSION), reply_markup=dimension_keyboard()
        )
        await state.set_state(DefectSG.measurement_dimension)

    @on.callback_query(F.data.in_({CB_MEAS_SKIP, CB_MEAS_DONE}))
    async def done(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()

        await callback.message.edit_text(
            str(M.ASK_DESCRIPTION), reply_markup=skip_keyboard(CB_DESC_SKIP)
        )
        await state.set_state(DefectSG.desc)
