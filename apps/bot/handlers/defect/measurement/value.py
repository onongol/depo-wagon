from typing import TYPE_CHECKING

from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.measurement import measurement_next_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.defects.constants import DIMENSION_UNITS

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message


async def receive_measurement_value(message: Message, state: FSMContext) -> None:
    """Receive measurement value as text, validate and save."""
    text = message.text.strip()

    try:
        value = float(text.replace(",", "."))
    except ValueError:
        await message.answer(str(M.VALUE_INVALID), parse_mode=M.PARSE_MODE)
        return

    defect = await load_defect(state)
    current = defect.current_measurement
    current.value = value
    current.unit = DIMENSION_UNITS.get(current.dimension, "")
    defect.measurements.append(current)
    defect.current_measurement = None
    await save_defect(state, defect)

    await message.answer(
        str(M.MEASUREMENT_SAVED).format(
            count=len(defect.measurements),
            label=current.dimension_label,
            value=current.value,
            unit=f" {current.unit}" if current.unit else "",
        ),
        parse_mode=M.PARSE_MODE,
        reply_markup=measurement_next_keyboard(),
    )
    await state.set_state(DefectSG.measurement_choice)
