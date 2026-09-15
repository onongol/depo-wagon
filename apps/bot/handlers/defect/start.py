from typing import TYPE_CHECKING

from apps.bot.fsm import save_defect
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.user_data import DefectData

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

    from apps.core.models import Employee


async def new_defect_start(
    message: Message, state: FSMContext, employee: Employee | None
) -> None:
    """Entry point: /new_defect or menu button."""
    if not employee:
        await message.answer(str(M.NOT_REGISTERED))
        return

    await save_defect(state, DefectData())
    await message.answer(str(M.NEW_DEFECT_START), parse_mode=M.PARSE_MODE)
    await state.set_state(DefectSG.wagon_num)
