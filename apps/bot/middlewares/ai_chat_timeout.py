"""Idle timeout for the AI chat.

PTB's ConversationHandler took conversation_timeout=600 and ended the
conversation on a timer. aiogram has no equivalent, so the check runs on the
next message instead. The difference is unobservable: state is only ever
inspected when a message arrives.

An outer middleware rather than a check inside the handler, because the ai_chat
router also owns the menu-text fallback. Checked inside, a menu button pressed
eleven minutes later would still be eaten by that fallback; returning UNHANDLED
here clears the state and lets the update carry on to the later routers, which
is what PTB's proactive timer produced.
"""

import time
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import UNHANDLED

from apps.bot.constants import UD_AI_CHAT_LAST
from apps.bot.states import AiChatSG

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext
    from aiogram.types import TelegramObject

AI_CHAT_TIMEOUT = 600.0


class AiChatTimeoutMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext = data["state"]

        if await state.get_state() == AiChatSG.chatting.state:
            last = (await state.get_data()).get(UD_AI_CHAT_LAST)
            if last is not None and time.time() - last > AI_CHAT_TIMEOUT:
                await state.clear()
                return UNHANDLED

        return await handler(event, data)
