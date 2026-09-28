from typing import TYPE_CHECKING, Any

from aiogram import F
from aiogram.fsm.scene import on

from apps.bot.callback_data import (
    CB_MEAS_BACK,
    CB_MEAS_CLEAR,
    CB_MEAS_DONE,
    CB_MEAS_SKIP,
    DimensionCB,
)
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.defect.scene import STEP_TEXT, DefectScene
from apps.bot.handlers.defect.text import (
    build_ask_value_text,
    build_measurements_text,
    build_value_invalid_text,
)
from apps.bot.keyboards.measurement import (
    measurement_keyboard,
    measurement_value_keyboard,
)
from apps.bot.states import DefectSG
from apps.bot.user_data import MeasurementEntry
from apps.defects.constants import DIMENSION_UNITS, MeasurementDimension

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery, Message

    from apps.bot.handlers.defect.scene import Screen
    from apps.bot.user_data import DefectData

_DIM_LABELS = dict(MeasurementDimension.choices)


class MeasurementChoiceScene(DefectScene, state=DefectSG.measurement_choice.state):
    """One card: a dimension, then its number; the card lists what is saved.

    A picked dimension is the form's current_measurement, not a state of its own.
    """

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        return DefectSG.photo

    @classmethod
    def back_to(cls, form: DefectData, data: dict[str, Any]) -> State | None:
        """While a number is asked for, the prompt's own Back returns to the card."""
        if form.current_measurement:
            return None
        return super().back_to(form, data)

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if current := form.current_measurement:
            text = build_ask_value_text(current.dimension_label, current.unit)
            return text, measurement_value_keyboard()

        any_saved = bool(form.measurements)
        clearable = any_saved and bool(data.get(UD_EDITING))
        text = build_measurements_text(form.measurements)
        return text, measurement_keyboard(any_saved=any_saved, clearable=clearable)

    async def _set_current(
        self,
        callback: CallbackQuery,
        state: FSMContext,
        current: MeasurementEntry | None,
    ) -> None:
        defect = await load_defect(state)
        defect.current_measurement = current
        await save_defect(state, defect)
        await self.show_as_edit(callback, state)

    @on.callback_query(DimensionCB.filter())
    async def pick(
        self, callback: CallbackQuery, callback_data: DimensionCB, state: FSMContext
    ) -> None:
        await callback.answer()

        dimension = callback_data.value
        current = MeasurementEntry(
            dimension=dimension,
            dimension_label=str(_DIM_LABELS.get(dimension, dimension)),
            unit=DIMENSION_UNITS.get(dimension, ""),
        )
        await self._set_current(callback, state, current)

    @on.callback_query(F.data == CB_MEAS_BACK)
    async def back(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await self._set_current(callback, state, None)

    @on.message(*STEP_TEXT)
    async def receive(self, message: Message, state: FSMContext) -> None:
        """The number for the picked dimension; any text before one shows the card."""
        defect = await load_defect(state)
        current = defect.current_measurement
        if current is None:
            await self.show_as_message(message, state)
            return

        try:
            current.value = float(message.text.strip().replace(",", "."))
        except ValueError:
            await message.answer(
                **build_value_invalid_text().as_kwargs(),
                reply_markup=measurement_value_keyboard(),
            )
            return

        defect.measurements.append(current)
        defect.current_measurement = None
        await save_defect(state, defect)
        await self.show_as_message(message, state)

    @on.callback_query(F.data.in_({CB_MEAS_SKIP, CB_MEAS_DONE}))
    async def done(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await self.go_on(state, DefectSG.desc)

    @on.callback_query(F.data == CB_MEAS_CLEAR)
    async def clear(self, callback: CallbackQuery, state: FSMContext) -> None:
        """An Edit's way to drop a wrong measurement: all of them, then add again."""
        await callback.answer()

        defect = await load_defect(state)
        defect.measurements = []
        defect.current_measurement = None
        await save_defect(state, defect)
        await self.show_as_edit(callback, state)
