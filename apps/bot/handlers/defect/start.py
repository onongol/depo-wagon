from typing import TYPE_CHECKING

from aiogram.types import ReplyKeyboardRemove

from apps.bot.constants import DEFECT_USER_DATA_KEYS, UD_FORM_HEADER, UD_SCREEN
from apps.bot.fsm import drop_keys, save_defect
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.user_data import DefectData
from apps.bot.utils.screens import close_screen

from .text import build_new_defect_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.scene import ScenesManager
    from aiogram.types import Message

    from apps.core.models import Employee

# Start over draws the blank form into the messages the last one had
_FORM_MESSAGES = (UD_SCREEN, UD_FORM_HEADER)


async def open_blank_form(state: FSMContext) -> None:
    """Also drops what an abandoned form left behind, UD_EDITING above all."""
    await drop_keys(
        state, *(key for key in DEFECT_USER_DATA_KEYS if key not in _FORM_MESSAGES)
    )
    await save_defect(state, DefectData())


async def new_defect_start(
    message: Message,
    state: FSMContext,
    employee: Employee | None,
    scenes: ScenesManager,
) -> None:
    if not employee:
        await message.answer(str(M.NOT_REGISTERED))
        return

    await close_screen(message.bot, state)
    await open_blank_form(state)
    # Not the step's screen: a message that hides the menu never takes inline buttons
    header = await message.answer(
        **build_new_defect_text().as_kwargs(), reply_markup=ReplyKeyboardRemove()
    )
    await state.update_data({UD_FORM_HEADER: [message.chat.id, header.message_id]})
    await scenes.enter(DefectSG.wagon_num)
