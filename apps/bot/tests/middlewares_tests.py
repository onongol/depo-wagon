"""Tests for the aiogram middlewares."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.dispatcher.event.bases import UNHANDLED

from apps.bot.middlewares import CloseOldConnectionsMiddleware

TARGET = "apps.bot.middlewares.db.close_old_connections"


class TestCloseOldConnectionsMiddleware:
    async def test_closes_connections_before_the_handler_runs(self):
        order = []
        middleware = CloseOldConnectionsMiddleware()

        async def handler(event, data):
            order.append("handler")
            return "result"

        with patch(TARGET, side_effect=lambda: order.append("close")):
            result = await middleware(handler, MagicMock(), {})

        assert order == ["close", "handler"]
        assert result == "result"

    async def test_passes_the_event_and_data_through_untouched(self):
        middleware = CloseOldConnectionsMiddleware()
        handler = AsyncMock(return_value=None)
        event = MagicMock()
        data = {"state": MagicMock()}

        with patch(TARGET):
            await middleware(handler, event, data)

        handler.assert_awaited_once_with(event, data)

    async def test_does_not_swallow_a_handler_exception(self):
        middleware = CloseOldConnectionsMiddleware()

        async def handler(event, data):
            msg = "boom"
            raise RuntimeError(msg)

        with patch(TARGET), pytest.raises(RuntimeError, match="boom"):
            await middleware(handler, MagicMock(), {})

    async def test_closes_once_per_call_not_per_handler_attempt(self):
        middleware = CloseOldConnectionsMiddleware()

        with patch(TARGET) as close:
            await middleware(AsyncMock(), MagicMock(), {})

        close.assert_called_once()


class TestAiChatTimeoutMiddleware:
    """Replaces ConversationHandler(conversation_timeout=600).

    PTB ended the session on a timer; this checks on the next message instead.
    Unobservable difference — state is only ever inspected when one arrives.
    """

    async def _call(self, state, handler=None):
        from apps.bot.middlewares import AiChatTimeoutMiddleware

        handler = handler or AsyncMock(return_value="handled")
        result = await AiChatTimeoutMiddleware()(handler, MagicMock(), {"state": state})
        return result, handler

    async def test_passes_through_outside_the_ai_chat(self, state):
        result, handler = await self._call(state)

        assert result == "handled"
        handler.assert_awaited_once()

    async def test_passes_through_while_the_session_is_fresh(self, state):
        from apps.bot.constants import UD_AI_CHAT_LAST
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)
        await state.update_data({UD_AI_CHAT_LAST: time.time()})

        result, handler = await self._call(state)

        assert result == "handled"
        handler.assert_awaited_once()

    async def test_expires_the_session_once_it_is_idle(self, state):
        from apps.bot.constants import UD_AI_CHAT_LAST
        from apps.bot.middlewares import AI_CHAT_TIMEOUT
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)
        await state.update_data({UD_AI_CHAT_LAST: time.time() - AI_CHAT_TIMEOUT - 1})

        result, handler = await self._call(state)

        assert result is UNHANDLED
        handler.assert_not_awaited()
        assert await state.get_state() is None

    async def test_an_expired_session_lets_the_update_reach_later_routers(self, state):
        """UNHANDLED is what makes a menu button fall through instead of being eaten."""
        from apps.bot.constants import UD_AI_CHAT_LAST
        from apps.bot.middlewares import AI_CHAT_TIMEOUT
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)
        await state.update_data({UD_AI_CHAT_LAST: time.time() - AI_CHAT_TIMEOUT - 1})

        result, _ = await self._call(state)

        assert result is UNHANDLED

    async def test_a_session_with_no_stamp_is_not_expired(self, state):
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)

        result, handler = await self._call(state)

        assert result == "handled"
        handler.assert_awaited_once()
