"""Tests for dispatcher assembly.

Replaces application_tests.py, which reached into PTB's handler table. The
router order is the part worth guarding: under PTB every precedence was
implicit in the order add_handler was called, and none of it was covered.
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatType
from aiogram.exceptions import ClientDecodeError, TelegramAPIError
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.types import Chat, Message, Update, User

from apps.bot.dispatcher import _BOT_COMMANDS, make_dispatcher, on_startup
from apps.bot.errors import build_session_error_text, error_handler
from apps.bot.messages import BotMessages as M


@pytest.fixture
def dispatcher():
    return make_dispatcher(MemoryStorage(), SimpleEventIsolation())


def _private_names(dispatcher) -> list[str]:
    """The private-chat routers in order: where every precedence lives."""
    (private,) = [r for r in dispatcher.sub_routers if r.name == "private"]
    return [r.name for r in private.sub_routers]


class TestEventsIsolation:
    def test_uses_the_isolation_it_is_given(self):
        """aiogram silently falls back to no isolation at all."""
        isolation = SimpleEventIsolation()

        dispatcher = make_dispatcher(MemoryStorage(), isolation)

        assert dispatcher.fsm.events_isolation is isolation


class TestTopLevelRouters:
    def test_private_chats_and_the_support_group_are_separate_trees(self, dispatcher):
        """Every handler lives under one of these, so the chat type is set once."""
        assert [r.name for r in dispatcher.sub_routers] == ["private", "support_group"]


class TestRouterOrder:
    def test_start_comes_before_everything_else(self, dispatcher):
        """So /start and the link buttons still work mid-conversation."""
        names = _private_names(dispatcher)

        assert names[0] == "start"

    @pytest.mark.parametrize("flow", ["defect_flow", "support", "ai_chat"])
    def test_cancel_comes_before_every_conversation(self, dispatcher, flow):
        """/cancel wins by registration order, ahead of every flow's own state."""
        names = _private_names(dispatcher)

        assert names.index("cancel") < names.index(flow)

    def test_help_comes_after_the_conversations(self, dispatcher):
        """The Help button inside a flow must reach that flow, not help_command."""
        names = _private_names(dispatcher)

        assert names.index("help") > names.index("ai_chat")

    def test_ai_chat_comes_before_help_so_its_fallback_wins(self, dispatcher):
        """The Help button pressed mid-session cancels, it does not show help."""
        names = _private_names(dispatcher)

        assert names.index("ai_chat") < names.index("help")

    def test_tasks_comes_after_start(self, dispatcher):
        """/start mid-list is answered by start, leaving the list on screen."""
        names = _private_names(dispatcher)

        assert names.index("tasks") > names.index("start")

    def test_stale_goes_last(self, dispatcher):
        """Anything registered after it would never be reached."""
        names = _private_names(dispatcher)

        assert names[-1] == "stale"

    def test_every_router_is_named_so_the_order_is_assertable(self, dispatcher):
        assert all(_private_names(dispatcher))


class TestMiddlewareAndHooks:
    def test_connections_are_closed_once_per_update_before_filters(self, dispatcher):
        from apps.bot.middlewares import CloseOldConnectionsMiddleware

        registered = dispatcher.update.outer_middleware[:]

        assert any(isinstance(m, CloseOldConnectionsMiddleware) for m in registered)

    def test_the_ai_chat_timeout_is_checked_before_any_router(self, dispatcher):
        """On a router, an earlier one claiming the update would skip the check."""
        from apps.bot.middlewares import AiChatTimeoutMiddleware

        registered = dispatcher.update.outer_middleware[:]

        assert any(isinstance(m, AiChatTimeoutMiddleware) for m in registered)

    @pytest.mark.parametrize("observer", ["message", "callback_query"])
    def test_the_employee_is_loaded_for_messages_and_callbacks(
        self, dispatcher, observer
    ):
        from apps.bot.middlewares import EmployeeMiddleware

        registered = getattr(dispatcher, observer).middleware[:]

        assert any(isinstance(m, EmployeeMiddleware) for m in registered)

    def test_the_error_handler_is_registered(self, dispatcher):
        assert dispatcher.errors.handlers

    async def test_the_error_handler_swallows_rather_than_reraises(self, caplog):
        event = _error_event(callback_query=None)

        with caplog.at_level(logging.ERROR):
            result = await error_handler(event, _bot())

        assert result is None
        assert "Unhandled exception" in caplog.text

    async def test_the_log_names_the_update_but_carries_nothing_personal(self, caplog):
        user = User(id=777, is_bot=False, first_name="Batbayar", username="bat_d")
        chat = Chat(id=777, type=ChatType.SUPERGROUP)
        message = Message(
            message_id=1,
            date=0,
            chat=chat,
            from_user=user,
            text="call me on +976 9911 2233",
        )
        event = MagicMock(
            update=Update(update_id=42, message=message), exception=RuntimeError()
        )

        with caplog.at_level(logging.ERROR):
            await error_handler(event, _bot(), chat)

        assert "update_id=42" in caplog.text
        for personal in ("Batbayar", "bat_d", "9911 2233"):
            assert personal not in caplog.text


def _error_event(callback_query=None):
    return MagicMock(
        update=MagicMock(update_id=1, callback_query=callback_query),
        exception=RuntimeError("boom"),
    )


def _bot():
    return MagicMock(send_message=AsyncMock())


def _chat(chat_type=ChatType.PRIVATE):
    return Chat(id=777, type=chat_type)


def _callback(**kwargs):
    return MagicMock(answer=AsyncMock(**kwargs))


def _telegram_error():
    return TelegramAPIError(method=MagicMock(), message="query is too old")


def _decode_error():
    """A proxy's HTML error page: aiogram cannot parse it, and it is no API error."""
    return ClientDecodeError("Failed to decode object", ValueError(), "<html>502")


class TestErrorHandlerTellsTheUser:
    async def test_a_private_chat_is_told(self):
        bot = _bot()

        await error_handler(_error_event(), bot, _chat())

        bot.send_message.assert_awaited_once_with(
            777, **build_session_error_text().as_kwargs()
        )

    async def test_a_callback_is_answered_and_told_in_the_chat(self):
        bot, callback = _bot(), _callback()

        await error_handler(_error_event(callback), bot, _chat())

        callback.answer.assert_awaited_once_with()
        bot.send_message.assert_awaited_once()

    @pytest.mark.parametrize("error", [_telegram_error(), _decode_error()])
    async def test_a_failed_answer_still_gets_the_message(self, error):
        """The failure this path exists for is slow enough to outlive the query."""
        bot, callback = _bot(), _callback(side_effect=error)

        await error_handler(_error_event(callback), bot, _chat())

        bot.send_message.assert_awaited_once()

    @pytest.mark.parametrize("error", [_telegram_error(), _decode_error()])
    async def test_a_failure_to_tell_the_user_is_swallowed(self, error):
        bot = _bot()
        bot.send_message.side_effect = error

        result = await error_handler(_error_event(), bot, _chat())

        assert result is None

    async def test_a_group_chat_is_left_alone(self):
        bot = _bot()

        await error_handler(_error_event(), bot, _chat(ChatType.SUPERGROUP))

        bot.send_message.assert_not_awaited()

    async def test_an_update_without_a_chat_is_still_answered(self):
        bot, callback = _bot(), _callback()

        await error_handler(_error_event(callback), bot, None)

        callback.answer.assert_awaited_once_with()
        bot.send_message.assert_not_awaited()


class TestStartupHook:
    def test_command_descriptions_are_held_lazily(self):
        """A gettext proxy in a BotCommand would fail at import, not at send."""
        assert all(not isinstance(d, str) for _command, d in _BOT_COMMANDS)

    async def test_publishes_commands_as_concrete_strings(self):
        bot = MagicMock(
            set_my_commands=AsyncMock(),
            set_chat_menu_button=AsyncMock(),
            set_my_description=AsyncMock(),
            set_my_short_description=AsyncMock(),
        )

        await on_startup(bot)

        published = bot.set_my_commands.await_args.args[0]
        assert [c.command for c in published] == [c for c, _d in _BOT_COMMANDS]
        assert all(type(c.description) is str for c in published)

    async def test_publishes_the_menu_button_and_descriptions(self):
        bot = MagicMock(
            set_my_commands=AsyncMock(),
            set_chat_menu_button=AsyncMock(),
            set_my_description=AsyncMock(),
            set_my_short_description=AsyncMock(),
        )

        await on_startup(bot)

        bot.set_chat_menu_button.assert_awaited_once()
        bot.set_my_description.assert_awaited_once_with(str(M.BOT_DESCRIPTION))
        bot.set_my_short_description.assert_awaited_once_with(
            str(M.BOT_SHORT_DESCRIPTION)
        )

    async def test_start_is_offered_first_in_the_command_menu(self):
        assert _BOT_COMMANDS[0][0] == "start"


class TestDefectRouterOrder:
    """The flow router must precede its own entry points.

    That ordering is what stopped PTB's entry point from restarting a
    conversation already in progress: BTN_NEW_DEFECT typed mid-flow reaches
    receive_wagon_number, whose MENU_TEXTS guard re-prompts, rather than
    wiping the half-filled form.
    """

    def test_flow_comes_before_entry(self, dispatcher):
        names = _private_names(dispatcher)

        assert names.index("defect_flow") < names.index("defect_entry")

    def test_flow_comes_after_start(self, dispatcher):
        """Link buttons keep working mid-flow, as they did under PTB."""
        names = _private_names(dispatcher)

        assert names.index("start") < names.index("defect_flow")

    def test_flow_comes_before_tasks(self, dispatcher):
        """1:1 with PTB: list pagination is inert while a defect is in progress."""
        names = _private_names(dispatcher)

        assert names.index("defect_flow") < names.index("tasks")

    def test_the_flow_catch_all_is_registered_last_within_the_flow(self):
        from apps.bot.handlers.defect.router import get_defect_flow_router

        router = get_defect_flow_router()
        callbacks = [h.callback.__name__ for h in router.callback_query.handlers]

        assert callbacks[-1] == "stale_callback"

    def test_every_defect_state_has_at_least_one_handler(self):
        """Guards against a step losing its route during the conversion."""
        from aiogram.filters import StateFilter

        from apps.bot.handlers.defect.router import get_defect_flow_router
        from apps.bot.states import DefectSG

        router = get_defect_flow_router()
        covered = set()
        for observer in (router.message, router.callback_query):
            for handler in observer.handlers:
                for flt in handler.filters or ():
                    if isinstance(flt.callback, StateFilter):
                        covered |= {
                            s.state if hasattr(s, "state") else s
                            for s in flt.callback.states
                        }

        # saving has no step of its own: the flow's catch-alls absorb what arrives.
        waiting = {DefectSG.saving.state}
        missing = {s.state for s in DefectSG.__states__} - covered - waiting
        assert not missing
