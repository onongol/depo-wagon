from typing import TYPE_CHECKING

from apps.bot.handlers.common.text import build_cancelled_text
from apps.bot.keyboards.menu import main_menu_keyboard

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message


async def cancel(message: Message, state: FSMContext) -> None:
    """Also brings the menu back, which the defect form hides."""
    await state.clear()
    await message.answer(
        **build_cancelled_text().as_kwargs(), reply_markup=main_menu_keyboard()
    )
