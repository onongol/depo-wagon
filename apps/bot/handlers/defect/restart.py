from typing import TYPE_CHECKING, Any

from apps.bot.keyboards.defect import defect_in_progress_keyboard
from apps.bot.utils.screens import edit_or_send

from .resume import show_current_step
from .start import open_blank_form
from .text import (
    build_defect_continued_text,
    build_defect_in_progress_text,
    build_new_defect_text,
)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message


async def defect_in_progress(message: Message) -> None:
    """New Defect while a form is open: ask rather than wipe it."""
    await message.answer(
        **build_defect_in_progress_text().as_kwargs(),
        reply_markup=defect_in_progress_keyboard(),
    )


async def continue_defect(callback: CallbackQuery, state: FSMContext) -> None:
    """The question turns into the step it interrupted."""
    await callback.answer()

    async def send(text: str, **kwargs: Any) -> None:
        await edit_or_send(callback, text=text, **kwargs)

    if not await show_current_step(send, state):
        await edit_or_send(callback, **build_defect_continued_text().as_kwargs())


async def restart_defect(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await open_blank_form(state)
    await edit_or_send(callback, **build_new_defect_text().as_kwargs())
