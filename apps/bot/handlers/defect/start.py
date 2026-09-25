from typing import TYPE_CHECKING

from aiogram.types import ReplyKeyboardRemove

from apps.bot.fsm import clear_defect_keys, save_defect
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.user_data import DefectData

from .text import build_new_defect_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

    from apps.core.models import Employee


async def open_blank_form(state: FSMContext) -> None:
    """Also drops what an abandoned form left behind, UD_EDITING above all."""
    await clear_defect_keys(state)
    await save_defect(state, DefectData())
    await state.set_state(DefectSG.wagon_num)


async def new_defect_start(
    message: Message, state: FSMContext, employee: Employee | None
) -> None:
    if not employee:
        await message.answer(str(M.NOT_REGISTERED))
        return

    await open_blank_form(state)
    # The menu is no answer to any step; every exit brings it back
    await message.answer(
        **build_new_defect_text().as_kwargs(), reply_markup=ReplyKeyboardRemove()
    )
