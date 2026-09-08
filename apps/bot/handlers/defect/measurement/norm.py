from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_NORM_SKIP, CB_UNIT_SKIP
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message


async def receive_norm_value(message: Message, state: FSMContext) -> None:
    """Receive norm value as text."""
    text = message.text.strip()

    try:
        norm = float(text.replace(",", "."))
    except ValueError:
        await message.answer(
            str(M.NORM_INVALID),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard(CB_NORM_SKIP),
        )
        return

    defect = await load_defect(state)
    defect.current_measurement.norm_value = norm
    await save_defect(state, defect)

    await message.answer(
        str(M.ASK_UNIT),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(CB_UNIT_SKIP),
    )
    await state.set_state(DefectSG.measurement_unit)


async def skip_norm_value(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip norm value."""
    await callback.answer()

    defect = await load_defect(state)
    defect.current_measurement.norm_value = None
    await save_defect(state, defect)

    await callback.message.edit_text(
        str(M.ASK_UNIT),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(CB_UNIT_SKIP),
    )
    await state.set_state(DefectSG.measurement_unit)
