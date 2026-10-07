from typing import TYPE_CHECKING

from apps.bot.states import SupportSG

from .text import build_support_ask_text, build_support_unavailable_text
from .utils import support_chat_id

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message


async def support_start(message: Message, state: FSMContext) -> None:
    """Entry: /support — ask the user to type their question."""
    if support_chat_id() is None:
        await message.answer(**build_support_unavailable_text().as_kwargs())
        return

    await message.answer(**build_support_ask_text().as_kwargs())
    await state.set_state(SupportSG.message)
