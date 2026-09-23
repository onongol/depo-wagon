"""Tests for the aiogram middlewares."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, InaccessibleMessage, Message

from apps.bot.middlewares import CloseOldConnectionsMiddleware

TARGET = "apps.bot.middlewares.db.close_old_connections"


class TestCloseOldConnectionsMiddleware:
    async def test_closes_connections_after_the_handler_runs(self):
        order = []
        middleware = CloseOldConnectionsMiddleware()

        async def handler(event, data):
            order.append("handler")
            return "result"

        with patch(TARGET, side_effect=lambda: order.append("close")):
            result = await middleware(handler, MagicMock(), {})

        assert order == ["handler", "close"]
        assert result == "result"

    async def test_closes_connections_even_when_the_handler_raises(self):
        middleware = CloseOldConnectionsMiddleware()

        async def handler(event, data):
            msg = "boom"
            raise RuntimeError(msg)

        with patch(TARGET) as close, pytest.raises(RuntimeError, match="boom"):
            await middleware(handler, MagicMock(), {})

        close.assert_called_once()

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

    async def _call(self, state, handler=None, data=None):
        from apps.bot.middlewares import AiChatTimeoutMiddleware

        handler = handler or AsyncMock(return_value="handled")
        data = data if data is not None else {}
        data.update({"state": state, "raw_state": await state.get_state()})
        result = await AiChatTimeoutMiddleware()(handler, MagicMock(), data)
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

        assert result == "handled"
        handler.assert_awaited_once()
        assert await state.get_state() is None

    async def test_an_expired_session_lets_the_update_reach_later_routers(self, state):
        """The cleared state must reach the filters, which read raw_state from data."""
        from apps.bot.constants import UD_AI_CHAT_LAST
        from apps.bot.middlewares import AI_CHAT_TIMEOUT
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)
        await state.update_data({UD_AI_CHAT_LAST: time.time() - AI_CHAT_TIMEOUT - 1})

        data = {}
        await self._call(state, data=data)

        assert data["raw_state"] is None

    async def test_an_event_with_no_fsm_context_passes_through(self):
        """Global now, so chat-only events reach it with no state resolved."""
        from apps.bot.middlewares import AiChatTimeoutMiddleware

        handler = AsyncMock(return_value="handled")

        result = await AiChatTimeoutMiddleware()(handler, MagicMock(), {})

        assert result == "handled"
        handler.assert_awaited_once()

    async def test_a_session_with_no_stamp_is_not_expired(self, state):
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)

        result, handler = await self._call(state)

        assert result == "handled"
        handler.assert_awaited_once()

    async def test_stamps_the_session_after_the_handler_runs(self, state):
        """The middleware owns the stamp now — no handler has to remember it."""
        from apps.bot.constants import UD_AI_CHAT_LAST
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)
        await state.update_data({UD_AI_CHAT_LAST: time.time() - 5})

        before = time.time()
        await self._call(state)

        assert (await state.get_data())[UD_AI_CHAT_LAST] >= before

    async def test_stamps_a_session_the_handler_just_started(self, state):
        """Covers ai_chat_start: not chatting on entry, chatting once handler returns."""
        from apps.bot.constants import UD_AI_CHAT_LAST
        from apps.bot.states import AiChatSG

        async def handler(event, data):
            await data["state"].set_state(AiChatSG.chatting)
            return "handled"

        before = time.time()
        await self._call(state, handler=handler)

        assert (await state.get_data())[UD_AI_CHAT_LAST] >= before

    async def test_does_not_stamp_a_session_the_handler_ended(self, state):
        """Covers cancel: the handler clears the state, so there's nothing to stamp."""
        from apps.bot.constants import UD_AI_CHAT_LAST
        from apps.bot.states import AiChatSG

        async def handler(event, data):
            await data["state"].clear()
            return "handled"

        await state.set_state(AiChatSG.chatting)
        await self._call(state, handler=handler)

        assert UD_AI_CHAT_LAST not in await state.get_data()


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

    async def test_an_expired_query_does_not_cost_the_notice(self, state):
        """The form is already cleared by then — the error handler would say the wrong thing."""
        from apps.bot.messages import BotMessages as M

        await self._store_stale_defect(state)
        callback = _spec_callback()
        callback.answer.side_effect = TelegramAPIError(
            method=MagicMock(), message="query is too old"
        )

        await self._call(state, event=callback)

        callback.message.edit_text.assert_awaited_once_with(str(M.FORM_OUTDATED))

    async def test_an_inaccessible_message_gets_a_fresh_notice(self, state):
        """Past 48 hours the message has no edit_text — it can only be answered."""
        from apps.bot.messages import BotMessages as M

        await self._store_stale_defect(state)
        callback = _spec_callback()
        callback.message = MagicMock(spec=InaccessibleMessage)
        callback.message.answer = AsyncMock()

        await self._call(state, event=callback)

        callback.message.answer.assert_awaited_once_with(str(M.FORM_OUTDATED))

    async def test_state_the_defect_flow_does_not_own_is_left_alone(self, state):
        from apps.bot.constants import UD_AI_CHAT_HISTORY

        await self._store_stale_defect(state)
        await state.update_data({UD_AI_CHAT_HISTORY: [{"q": "a"}]})

        await self._call(state)

        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == [{"q": "a"}]


async def _takes_employee(message, employee):
    pass


async def _takes_no_employee(message):
    pass


class TestEmployeeMiddleware:
    LOOKUP = "apps.bot.middlewares.employee.services.get_employee_by_telegram_id"

    async def _call(self, callback, *, event=None, lookup=None, user_id=777):
        from aiogram.dispatcher.event.handler import HandlerObject

        from apps.bot.middlewares import EmployeeMiddleware

        handler = AsyncMock(return_value="handled")
        data = {
            "handler": HandlerObject(callback=callback),
            "event_from_user": MagicMock(id=user_id) if user_id else None,
        }
        lookup = lookup or AsyncMock(return_value=None)
        with patch(self.LOOKUP, lookup):
            result = await EmployeeMiddleware()(handler, event or _spec_message(), data)
        return result, handler, data, lookup

    async def test_hands_the_employee_to_a_handler_that_takes_one(self):
        employee = MagicMock()

        result, handler, data, lookup = await self._call(
            _takes_employee, lookup=AsyncMock(return_value=employee)
        )

        assert result == "handled"
        assert data["employee"] is employee
        lookup.assert_awaited_once_with(777)
        handler.assert_awaited_once()

    async def test_a_chat_without_an_employee_gets_none(self):
        result, handler, data, _ = await self._call(_takes_employee)

        assert result == "handled"
        assert data["employee"] is None
        handler.assert_awaited_once()

    async def test_reads_the_employee_on_every_update(self):
        from aiogram.dispatcher.event.handler import HandlerObject

        from apps.bot.middlewares import EmployeeMiddleware

        middleware = EmployeeMiddleware()
        lookup = AsyncMock(return_value=MagicMock())

        with patch(self.LOOKUP, lookup):
            for _ in range(2):
                data = {
                    "handler": HandlerObject(callback=_takes_employee),
                    "event_from_user": MagicMock(id=777),
                }
                await middleware(AsyncMock(), _spec_message(), data)

        assert lookup.await_count == 2

    async def test_skips_the_lookup_for_a_handler_that_takes_no_employee(self):
        result, handler, data, lookup = await self._call(_takes_no_employee)

        assert result == "handled"
        assert "employee" not in data
        lookup.assert_not_awaited()
        handler.assert_awaited_once()

    async def test_an_update_without_a_user_gets_none_without_a_lookup(self):
        _, handler, data, lookup = await self._call(_takes_employee, user_id=None)

        assert data["employee"] is None
        lookup.assert_not_awaited()
        handler.assert_awaited_once()

    async def test_a_failed_lookup_is_left_to_the_error_handler(self):
        from aiogram.dispatcher.event.handler import HandlerObject

        from apps.bot.middlewares import EmployeeMiddleware

        handler = AsyncMock()
        data = {
            "handler": HandlerObject(callback=_takes_employee),
            "event_from_user": MagicMock(id=777),
        }
        lookup = AsyncMock(side_effect=RuntimeError("db down"))

        with patch(self.LOOKUP, lookup), pytest.raises(RuntimeError, match="db down"):
            await EmployeeMiddleware()(handler, _spec_message(), data)

        handler.assert_not_awaited()
