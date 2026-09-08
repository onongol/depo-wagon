from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_NORM_SKIP
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

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
    defect.current_measurement.value = value
    await save_defect(state, defect)

    await message.answer(str(M.ASK_NORM), reply_markup=skip_keyboard(CB_NORM_SKIP))
    await state.set_state(DefectSG.measurement_norm)
