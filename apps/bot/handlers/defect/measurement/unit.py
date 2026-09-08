from typing import TYPE_CHECKING

from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import measurement_next_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

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


async def receive_unit(message: Message, state: FSMContext) -> None:
    """Receive unit as text."""
    defect = await load_defect(state)
    defect.current_measurement.unit = message.text.strip()
    text = _save_measurement(defect)
    await save_defect(state, defect)

    await message.answer(
        text, parse_mode=M.PARSE_MODE, reply_markup=measurement_next_keyboard()
    )
    await state.set_state(DefectSG.measurement_choice)


async def skip_unit(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip unit."""
    await callback.answer()

    defect = await load_defect(state)
    defect.current_measurement.unit = ""
    text = _save_measurement(defect)
    await save_defect(state, defect)

    await callback.message.edit_text(
        text, parse_mode=M.PARSE_MODE, reply_markup=measurement_next_keyboard()
    )
    await state.set_state(DefectSG.measurement_choice)
