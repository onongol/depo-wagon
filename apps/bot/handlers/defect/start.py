import logging
from typing import TYPE_CHECKING

from apps.bot.fsm import save_defect
from apps.bot.handlers.employee import get_employee
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.user_data import DefectData

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

logger = logging.getLogger(__name__)


async def new_defect_start(message: Message, state: FSMContext) -> None:
    """Entry point: /new_defect or menu button."""
    try:
        employee = await get_employee(message.from_user.id)
    except Exception:
        logger.exception("Failed to fetch employee in new_defect_start")
        await message.answer(str(M.SESSION_ERROR))
        return

    if not employee:
        await message.answer(str(M.NOT_REGISTERED))
        return

    await save_defect(state, DefectData())
    await message.answer(str(M.NEW_DEFECT_START), parse_mode=M.PARSE_MODE)
    await state.set_state(DefectSG.wagon_num)
