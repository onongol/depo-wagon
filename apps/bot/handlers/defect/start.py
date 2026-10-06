from typing import TYPE_CHECKING

from aiogram import flags

from apps.bot.constants import DEFECT_USER_DATA_KEYS, UD_SCREEN
from apps.bot.fsm import drop_keys, save_defect
from apps.bot.states import DefectSG
from apps.bot.user_data import DefectData
from apps.bot.utils.screens import close_screen

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.scene import ScenesManager
    from aiogram.types import Message


async def open_blank_form(state: FSMContext) -> None:
    """Drops an abandoned form's keys but the screen, which Start over reuses."""
    await drop_keys(state, *(key for key in DEFECT_USER_DATA_KEYS if key != UD_SCREEN))
    await save_defect(state, DefectData())


@flags.registered
async def new_defect_start(
    message: Message, state: FSMContext, scenes: ScenesManager
) -> None:
    await close_screen(message.bot, state)
    await open_blank_form(state)
    await scenes.enter(DefectSG.wagon_num)
