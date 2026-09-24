import contextlib
import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError

from apps.bot.constants import UD_AI_CHAT_HISTORY
from apps.bot.messages import BotMessages as M
from apps.bot.states import AiChatSG

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

    from apps.core.models import Employee

logger = logging.getLogger(__name__)


async def ai_chat_start(
    message: Message, state: FSMContext, employee: Employee | None
) -> None:
    if not employee:
        with contextlib.suppress(TelegramAPIError):
            await message.answer(str(M.NOT_REGISTERED))
        return

    await state.update_data({UD_AI_CHAT_HISTORY: []})

    try:
        await message.answer(str(M.AI_CHAT_GREETING), parse_mode=M.PARSE_MODE)
    except TelegramAPIError:
        logger.warning("Could not send greeting for employee %s", employee.id)
        return

    await state.set_state(AiChatSG.chatting)
