"""The shared step handlers for the steps not yet Scenes; DefectScene has its own."""

from typing import TYPE_CHECKING, Any

from apps.bot.states import DefectSG
from apps.bot.utils.screens import edit_or_send

from .resume import show_current_step
from .start import open_blank_form
from .text import build_defect_continued_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.scene import ScenesManager
    from aiogram.types import CallbackQuery, Message


async def menu_button_mid_flow(message: Message, state: FSMContext) -> None:
    """Every other menu button and command but /cancel shows the step again.

    The form stays in front until it ends; /cancel is the way out of it.
    """
    if not await show_current_step(message.answer, state):
        await message.answer(**build_defect_continued_text().as_kwargs())


async def continue_defect(callback: CallbackQuery, state: FSMContext) -> None:
    """The question turns into the step it interrupted."""
    await callback.answer()

    async def send(text: str, **kwargs: Any) -> None:
        await edit_or_send(callback, text=text, **kwargs)

    if not await show_current_step(send, state):
        await edit_or_send(callback, **build_defect_continued_text().as_kwargs())


async def restart_defect(
    callback: CallbackQuery, state: FSMContext, scenes: ScenesManager
) -> None:
    await callback.answer()
    await open_blank_form(state)
    await scenes.enter(DefectSG.wagon_num)
