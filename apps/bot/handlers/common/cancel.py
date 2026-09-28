from typing import TYPE_CHECKING

from apps.bot.handlers.common.text import build_cancelled_text
from apps.bot.keyboards.menu import main_menu_keyboard

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message


async def cancel(message: Message, state: FSMContext) -> None:
    """/cancel and the defect form's Cancel button; brings the menu back."""
    await state.clear()
    await message.answer(
        **build_cancelled_text().as_kwargs(), reply_markup=main_menu_keyboard()
    )
