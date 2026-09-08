from typing import TYPE_CHECKING

from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message


async def cancel(message: Message, state: FSMContext) -> None:
    """Cancel any active conversation and drop everything it stored.

    state.clear() rather than clearing selected keys: this is the blanket
    cancel, and PTB's version called user_data.clear() outright.
    """
    await state.clear()
    await message.answer(str(M.CANCELLED), parse_mode=M.PARSE_MODE)
