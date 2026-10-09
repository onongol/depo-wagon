import logging
from typing import TYPE_CHECKING

from aiogram import flags
from aiogram.exceptions import TelegramAPIError

from apps.bot.constants import FSMKey
from apps.bot.states import AiChatSG

from .text import build_ai_chat_greeting_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

logger = logging.getLogger(__name__)


@flags.registered
async def ai_chat_start(message: Message, state: FSMContext) -> None:
    await state.update_data({FSMKey.AI_CHAT_HISTORY: []})

    try:
        await message.answer(**build_ai_chat_greeting_text().as_kwargs())
    except TelegramAPIError:
        logger.warning("Could not send the AI chat greeting")
        return

    await state.set_state(AiChatSG.chatting)
