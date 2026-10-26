"""Tests for the aiogram middlewares."""

import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import flags
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import CallbackQuery, Message

from apps.bot.constants import FSMKey
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.middlewares import CloseOldConnectionsMiddleware, InFlightMiddleware
from apps.bot.middlewares.defect_form import (
    build_form_lost_text,
    build_form_outdated_text,
)
from apps.bot.states import AiChatSG, DefectSG, SupportSG
from apps.bot.tests.builders import (
    CHAT_ID,
    MESSAGE_ID,
    make_bad_request,
    make_callback,
)
from apps.bot.utils.unregistered import build_not_registered_text

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


class TestInFlightMiddleware:
    async def test_tracks_the_task_only_while_the_handler_runs(self):
        middleware = InFlightMiddleware()
        seen = []

        async def handler(event, data):
            seen.append(asyncio.current_task() in middleware.tasks)
            return "result"

        result = await middleware(handler, MagicMock(), {})

        assert result == "result"
        assert seen == [True]
        assert not middleware.tasks

    async def test_forgets_the_task_when_the_handler_raises(self):
        middleware = InFlightMiddleware()

        with pytest.raises(RuntimeError):
            await middleware(AsyncMock(side_effect=RuntimeError), MagicMock(), {})

        assert not middleware.tasks

    async def test_drain_returns_at_once_when_nothing_runs(self):
        await asyncio.wait_for(InFlightMiddleware(drain_timeout=60).drain(), 0.1)

    async def test_drain_waits_for_a_running_handler(self):
        middleware = InFlightMiddleware()
        release = asyncio.Event()
        done = []

        async def handler(event, data):
            await release.wait()
            done.append(True)

        task = asyncio.create_task(middleware(handler, MagicMock(), {}))
        await asyncio.sleep(0)
        asyncio.get_running_loop().call_later(0.01, release.set)

        await middleware.drain()

        assert done == [True]
        assert task.done()

    async def test_drain_gives_up_after_the_timeout(self, caplog):
        middleware = InFlightMiddleware(drain_timeout=0.01)
        never = asyncio.Event()

        async def handler(event, data):
            await never.wait()

        task = asyncio.create_task(middleware(handler, MagicMock(), {}))
        await asyncio.sleep(0)

        with caplog.at_level(logging.WARNING):
            await middleware.drain()

        assert not task.done()
        assert "1 update(s) still running" in caplog.text
        task.cancel()


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
        from apps.bot.constants import FSMKey
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)
        await state.update_data({FSMKey.AI_CHAT_LAST: time.time()})

        result, handler = await self._call(state)

        assert result == "handled"
        handler.assert_awaited_once()

    async def test_expires_the_session_once_it_is_idle(self, state):
        from apps.bot.constants import FSMKey
        from apps.bot.middlewares import AI_CHAT_TIMEOUT
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)
        await state.update_data(
            {FSMKey.AI_CHAT_LAST: time.time() - AI_CHAT_TIMEOUT - 1}
        )

        result, handler = await self._call(state)

        assert result == "handled"
        handler.assert_awaited_once()
        assert await state.get_state() is None

    async def test_an_expired_session_lets_the_update_reach_later_routers(self, state):
        """The cleared state must reach the filters, which read raw_state from data."""
        from apps.bot.constants import FSMKey
        from apps.bot.middlewares import AI_CHAT_TIMEOUT
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)
        await state.update_data(
            {FSMKey.AI_CHAT_LAST: time.time() - AI_CHAT_TIMEOUT - 1}
        )

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
        from apps.bot.constants import FSMKey
        from apps.bot.states import AiChatSG

        await state.set_state(AiChatSG.chatting)
        await state.update_data({FSMKey.AI_CHAT_LAST: time.time() - 5})

        before = time.time()
        await self._call(state)

        assert (await state.get_data())[FSMKey.AI_CHAT_LAST] >= before

    async def test_stamps_a_session_the_handler_just_started(self, state):
        """Covers ai_chat_start: not chatting on entry, chatting once handler returns."""
        from apps.bot.constants import FSMKey
        from apps.bot.states import AiChatSG

        async def handler(event, data):
            await data["state"].set_state(AiChatSG.chatting)
            return "handled"

        before = time.time()
        await self._call(state, handler=handler)

        assert (await state.get_data())[FSMKey.AI_CHAT_LAST] >= before

    async def test_does_not_stamp_a_session_the_handler_ended(self, state):
        """Covers cancel: the handler clears the state, so there's nothing to stamp."""
        from apps.bot.constants import FSMKey
        from apps.bot.states import AiChatSG

        async def handler(event, data):
            await data["state"].clear()
            return "handled"

        await state.set_state(AiChatSG.chatting)
        await self._call(state, handler=handler)

        assert FSMKey.AI_CHAT_LAST not in await state.get_data()


def _spec_message() -> MagicMock:
    """spec'd, unlike the shared builders: the middleware branches on isinstance."""
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    message.chat = MagicMock(id=777)
    message.message_id = 5
    return message


def _spec_callback() -> MagicMock:
    callback = MagicMock(spec=CallbackQuery)
    callback.answer = AsyncMock()
    callback.message = _spec_message()
    callback.bot = MagicMock(edit_message_reply_markup=AsyncMock())
    return callback


class TestDefectFormMiddleware:
    """The one None check for the whole flow: no step makes its own.

    load_defect returns None for a form an older build wrote or one that is
    gone, and every step would dereference it. The reset therefore has to land
    before the handler, which is why this is a middleware.
    """

    async def _call(self, state, event=None, handler=None):
        from apps.bot.middlewares import DefectFormMiddleware

        handler = handler or AsyncMock(return_value="handled")
        event = event if event is not None else _spec_message()
        data = {"state": state, "raw_state": await state.get_state()}
        result = await DefectFormMiddleware()(handler, event, data)
        return result, handler

    async def _store_stale_defect(self, state, at=DefectSG.node):
        from apps.bot.constants import FSMKey
        from apps.bot.user_data import STATE_SCHEMA_VERSION, DefectData

        stored = DefectData(wagon_number="60123456").to_dict()
        stored["_schema"] = STATE_SCHEMA_VERSION + 1
        await state.update_data({FSMKey.DEFECT: stored})
        await state.set_state(at)

    async def test_passes_through_outside_the_flow_when_no_form_is_stored(self, state):
        result, handler = await self._call(state)

        assert result == "handled"
        handler.assert_awaited_once()

    async def test_a_step_without_its_form_is_never_reached(self, state):
        """State and form keys expire apart, and a two-write exit can fail midway."""
        await state.set_state(DefectSG.measurement_choice)
        message = _spec_message()

        result, handler = await self._call(state, event=message)

        assert result is None
        handler.assert_not_awaited()
        assert await state.get_state() is None
        message.answer.assert_awaited_once_with(
            **build_form_lost_text().as_kwargs(), reply_markup=main_menu_keyboard()
        )

    async def test_a_tap_without_its_form_is_told_so_below_it(self, state):
        await state.set_state(DefectSG.department)
        callback = _spec_callback()

        await self._call(state, event=callback)

        callback.answer.assert_awaited_once_with()
        callback.message.answer.assert_awaited_once_with(
            **build_form_lost_text().as_kwargs(), reply_markup=main_menu_keyboard()
        )

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

    async def test_a_form_left_behind_outside_the_flow_does_not_claim_the_update(
        self, state
    ):
        """Failed saves and /ask mid-form leave it; /help must still get help."""
        await self._store_stale_defect(state, at=None)
        message = _spec_message()

        result, handler = await self._call(state, event=message)

        assert result == "handled"
        handler.assert_awaited_once()
        message.answer.assert_not_awaited()

    async def test_another_flow_keeps_its_state_and_loses_only_the_form(self, state):
        from apps.bot.constants import FSMKey

        await self._store_stale_defect(state, at=SupportSG.message)

        await self._call(state)

        assert FSMKey.DEFECT not in await state.get_data()
        assert await state.get_state() == SupportSG.message.state

    async def test_a_stale_form_is_dropped_and_the_state_reset(self, state):
        from apps.bot.fsm import load_defect

        await self._store_stale_defect(state, at=DefectSG.severity)

        await self._call(state)

        assert await load_defect(state) is None
        assert await state.get_state() is None

    async def test_the_user_is_told_rather_than_left_guessing(self, state):
        await self._store_stale_defect(state)
        message = _spec_message()

        await self._call(state, event=message)

        message.answer.assert_awaited_once_with(
            **build_form_outdated_text().as_kwargs(), reply_markup=main_menu_keyboard()
        )

    async def test_a_tap_gets_its_buttons_stripped_and_the_menu_back(self, state):
        """An edit carries no reply keyboard, so the notice is a new message."""
        await self._store_stale_defect(state)
        callback = _spec_callback()

        await self._call(state, event=callback)

        callback.answer.assert_awaited_once_with()
        callback.bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=None,
        )
        callback.message.answer.assert_awaited_once_with(
            **build_form_outdated_text().as_kwargs(), reply_markup=main_menu_keyboard()
        )

    async def test_an_expired_query_does_not_cost_the_notice(self, state):
        """The form is already cleared by then — the error handler would say the wrong thing."""
        await self._store_stale_defect(state)
        callback = _spec_callback()
        callback.answer.side_effect = make_bad_request("Bad Request: query is too old")

        await self._call(state, event=callback)

        callback.message.answer.assert_awaited_once()

    async def test_state_the_defect_flow_does_not_own_is_left_alone(self, state):
        from apps.bot.constants import FSMKey

        await self._store_stale_defect(state)
        await state.update_data({FSMKey.AI_CHAT_HISTORY: [{"q": "a"}]})

        await self._call(state)

        assert (await state.get_data())[FSMKey.AI_CHAT_HISTORY] == [{"q": "a"}]


async def _takes_employee(message, employee):
    pass


async def _takes_no_employee(message):
    pass


@flags.registered
async def _registered_only(message, employee):
    pass


@flags.registered
async def _registered_only_without_employee(message):
    pass


class TestEmployeeMiddleware:
    LOOKUP = "apps.bot.middlewares.employee.services.get_employee_by_telegram_id"

    async def _call(
        self, callback, *, event=None, lookup=None, user_id=777, extra=None
    ):
        """extra: more of the dispatcher's data, such as the chat's state."""
        from aiogram.dispatcher.event.handler import HandlerObject

        from apps.bot.middlewares import EmployeeMiddleware

        handler = AsyncMock(return_value="handled")
        data = {
            "handler": HandlerObject(callback=callback),
            "event_from_user": MagicMock(id=user_id) if user_id else None,
            **(extra or {}),
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

    async def test_looks_through_a_scene_handler_to_its_method(self):
        """A scene wraps each handler in something that takes **kwargs."""
        from aiogram.fsm.scene import SceneHandlerWrapper

        from apps.bot.handlers.defect.summary import SummaryScene

        save = SceneHandlerWrapper(SummaryScene, SummaryScene.save)
        decline = SceneHandlerWrapper(SummaryScene, SummaryScene.decline)

        _, _, saving, save_lookup = await self._call(save)
        _, _, declining, decline_lookup = await self._call(decline)

        assert saving["employee"] is None
        save_lookup.assert_awaited_once_with(777)
        assert "employee" not in declining
        decline_lookup.assert_not_awaited()

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

    async def test_a_registered_only_handler_is_never_handed_none(self):
        message = _spec_message()

        result, handler, data, _ = await self._call(_registered_only, event=message)

        assert result is None
        handler.assert_not_awaited()
        assert "employee" not in data
        message.answer.assert_awaited_once_with(
            **build_not_registered_text().as_kwargs()
        )

    async def test_a_refused_tap_is_answered_and_its_message_replaced(self):
        callback = make_callback()

        await self._call(_registered_only, event=callback)

        callback.answer.assert_awaited_once_with()
        callback.bot.edit_message_text.assert_awaited_once_with(
            chat_id=CHAT_ID,
            message_id=MESSAGE_ID,
            reply_markup=None,
            **build_not_registered_text().as_kwargs(),
        )

    async def test_a_refusal_ends_the_chats_flow(self, state):
        """Unlinked mid-session, the chat would be refused at every message."""
        await state.set_state(AiChatSG.chatting)
        await state.update_data({FSMKey.AI_CHAT_HISTORY: [{"role": "user"}]})

        await self._call(_registered_only, extra={"state": state})

        assert await state.get_state() is None
        assert await state.get_data() == {}

    async def test_a_refusal_ends_the_flow_even_if_the_reply_fails(self, state):
        await state.set_state(AiChatSG.chatting)
        message = _spec_message()
        message.answer = AsyncMock(
            side_effect=TelegramNetworkError(method=None, message="network")
        )

        with pytest.raises(TelegramNetworkError):
            await self._call(_registered_only, event=message, extra={"state": state})

        assert await state.get_state() is None

    async def test_a_registered_only_handler_gets_its_employee(self):
        employee = MagicMock()

        result, _, data, _ = await self._call(
            _registered_only, lookup=AsyncMock(return_value=employee)
        )

        assert result == "handled"
        assert data["employee"] is employee

    async def test_the_flag_alone_asks_for_the_lookup(self):
        """A handler may need a registered chat without needing its employee."""
        result, _, _, lookup = await self._call(
            _registered_only_without_employee,
            lookup=AsyncMock(return_value=MagicMock()),
        )

        assert result == "handled"
        lookup.assert_awaited_once_with(777)
