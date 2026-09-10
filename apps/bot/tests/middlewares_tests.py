"""Tests for the aiogram middlewares."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message

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


def _spec_message() -> MagicMock:
    """spec'd, unlike the shared builders: the middleware branches on isinstance."""
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    return message


def _spec_callback() -> MagicMock:
    callback = MagicMock(spec=CallbackQuery)
    callback.answer = AsyncMock()
    callback.message = _spec_message()
    return callback


class TestStaleSchemaMiddleware:
    """Guards the steps that assign onto the form without a None check.

    load_defect returns None for a form an older build wrote, and most of the
    flow would dereference it. The reset therefore has to land before the
    handler, which is why this is a middleware and not a guard inside a step.
    """

    async def _call(self, state, event=None, handler=None):
        from apps.bot.middlewares import StaleSchemaMiddleware

        handler = handler or AsyncMock(return_value="handled")
        event = event if event is not None else _spec_message()
        result = await StaleSchemaMiddleware()(handler, event, {"state": state})
        return result, handler

    async def _store_stale_defect(self, state):
        from apps.bot.constants import UD_DEFECT
        from apps.bot.user_data import STATE_SCHEMA_VERSION, DefectData

        stored = DefectData(wagon_number="60123456").to_dict()
        stored["_schema"] = STATE_SCHEMA_VERSION + 1
        await state.update_data({UD_DEFECT: stored})

    async def test_passes_through_when_no_form_is_stored(self, state):
        result, handler = await self._call(state)

        assert result == "handled"
        handler.assert_awaited_once()

    async def test_passes_through_a_form_this_build_wrote(self, state):
        from apps.bot.fsm import save_defect
        from apps.bot.user_data import DefectData

        await save_defect(state, DefectData(wagon_number="60123456"))

        result, handler = await self._call(state)

        assert result == "handled"
        handler.assert_awaited_once()

    async def test_a_stale_form_never_reaches_the_step(self, state):
        await self._store_stale_defect(state)

        result, handler = await self._call(state)

        assert result is None
        handler.assert_not_awaited()

    async def test_a_stale_form_is_dropped_and_the_state_reset(self, state):
        from apps.bot.fsm import load_defect
        from apps.bot.states import DefectSG

        await self._store_stale_defect(state)
        await state.set_state(DefectSG.severity)

        await self._call(state)

        assert await load_defect(state) is None
        assert await state.get_state() is None

    async def test_the_user_is_told_rather_than_left_guessing(self, state):
        from apps.bot.messages import BotMessages as M

        await self._store_stale_defect(state)
        message = _spec_message()

        await self._call(state, event=message)

        message.answer.assert_awaited_once_with(str(M.FORM_OUTDATED))

    async def test_a_callback_is_answered_and_its_keyboard_replaced(self, state):
        from apps.bot.messages import BotMessages as M

        await self._store_stale_defect(state)
        callback = _spec_callback()

        await self._call(state, event=callback)

        callback.answer.assert_awaited_once_with()
        callback.message.edit_text.assert_awaited_once_with(str(M.FORM_OUTDATED))

    async def test_a_failed_edit_still_reaches_the_user(self, state):
        """The message may be too old to edit — this fires at a deploy boundary."""
        from apps.bot.messages import BotMessages as M

        await self._store_stale_defect(state)
        callback = _spec_callback()
        callback.message.edit_text.side_effect = TelegramAPIError(
            method=MagicMock(), message="too old"
        )

        await self._call(state, event=callback)

        callback.message.answer.assert_awaited_once_with(str(M.FORM_OUTDATED))

    async def test_state_the_defect_flow_does_not_own_is_left_alone(self, state):
        from apps.bot.constants import UD_AI_CHAT_HISTORY

        await self._store_stale_defect(state)
        await state.update_data({UD_AI_CHAT_HISTORY: [{"q": "a"}]})

        await self._call(state)

        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == [{"q": "a"}]
