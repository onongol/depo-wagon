from typing import TYPE_CHECKING

from apps.bot.handlers.common.text import build_cancelled_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message


async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(**build_cancelled_text().as_kwargs())
