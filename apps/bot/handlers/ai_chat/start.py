import logging
from typing import TYPE_CHECKING

from aiogram import flags
from aiogram.exceptions import TelegramAPIError

from apps.bot.constants import UD_AI_CHAT_HISTORY
from apps.bot.states import AiChatSG

from .text import build_ai_chat_greeting_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

    from apps.core.models import Employee

logger = logging.getLogger(__name__)


@flags.registered
async def ai_chat_start(
    message: Message, state: FSMContext, employee: Employee
) -> None:
    await state.update_data({UD_AI_CHAT_HISTORY: []})

    try:
        await message.answer(**build_ai_chat_greeting_text().as_kwargs())
    except TelegramAPIError:
        logger.warning("Could not send greeting for employee %s", employee.id)
        return

    await state.set_state(AiChatSG.chatting)
