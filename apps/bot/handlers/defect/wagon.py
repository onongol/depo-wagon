from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import department_keyboard
from apps.bot.states import DefectSG

from .summary import show_summary
from .text import build_wagon_confirmed_text, build_wagon_not_found_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message


async def receive_wagon_number(message: Message, state: FSMContext) -> None:
    """Look up the typed wagon number; menu buttons never reach this step."""
    number = message.text.strip()
    wagon = await services.get_wagon_by_number(number)
    if not wagon:
        await message.answer(**build_wagon_not_found_text(number).as_kwargs())
        return

    defect = await load_defect(state)
    defect.wagon_id = wagon.id
    defect.wagon_number = wagon.number
    await save_defect(state, defect)

    if (await state.get_data()).get(UD_EDITING):
        await show_summary(message.answer, state, defect)
        return

    await message.answer(
        **build_wagon_confirmed_text(wagon.number).as_kwargs(),
        reply_markup=department_keyboard(),
    )
    await state.set_state(DefectSG.department)
