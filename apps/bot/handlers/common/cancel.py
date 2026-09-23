from typing import TYPE_CHECKING

from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message


async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(str(M.CANCELLED), parse_mode=M.PARSE_MODE)
