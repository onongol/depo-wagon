import contextlib
import logging
import time
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError

from apps.bot.constants import UD_AI_CHAT_HISTORY, UD_AI_CHAT_LAST
from apps.bot.handlers.employee import get_employee
from apps.bot.messages import BotMessages as M
from apps.bot.states import AiChatSG

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

logger = logging.getLogger(__name__)


async def ai_chat_start(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id

    try:
        employee = await get_employee(user_id)
    except Exception:
        logger.exception("Failed to fetch employee for user %s", user_id)
        return

    if not employee:
        with contextlib.suppress(TelegramAPIError):
            await message.answer(str(M.AI_CHAT_NOT_AUTHENTICATED))
        return

    await state.update_data({UD_AI_CHAT_HISTORY: [], UD_AI_CHAT_LAST: time.time()})

    try:
        await message.answer(str(M.AI_CHAT_GREETING), parse_mode=M.PARSE_MODE)
    except TelegramAPIError:
        logger.warning("Could not send greeting for user %s", user_id)
        return

    await state.set_state(AiChatSG.chatting)
