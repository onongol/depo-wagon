"""Tests for dispatcher assembly.

Replaces application_tests.py, which reached into PTB's handler table. The
router order is the part worth guarding: under PTB every precedence was
implicit in the order add_handler was called, and none of it was covered.
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.storage.memory import MemoryStorage

from apps.bot.dispatcher import _BOT_COMMANDS, make_dispatcher, on_startup
from apps.bot.handlers.common.error import error_handler
from apps.bot.messages import BotMessages as M


@pytest.fixture
def dispatcher():
    return make_dispatcher(MemoryStorage())


class TestRouterOrder:
    def test_start_comes_before_everything_else(self, dispatcher):
        """So /start and the link buttons still work mid-conversation."""
        names = [r.name for r in dispatcher.sub_routers]

        assert names[0] == "start"

    def test_utility_comes_after_the_conversations(self, dispatcher):
        """The Help button inside a flow must reach that flow, not help_command."""
        names = [r.name for r in dispatcher.sub_routers]

        assert names.index("utility") > names.index("ai_chat")

    def test_ai_chat_comes_before_utility_so_its_fallback_wins(self, dispatcher):
        """The Help button pressed mid-session cancels, it does not show help."""
        names = [r.name for r in dispatcher.sub_routers]

        assert names.index("ai_chat") < names.index("utility")

    def test_tasks_comes_after_start(self, dispatcher):
        """/start mid-list is answered by start, leaving the list on screen."""
        names = [r.name for r in dispatcher.sub_routers]

        assert names.index("tasks") > names.index("start")

    def test_stale_goes_last(self, dispatcher):
        """Anything registered after it would never be reached."""
        names = [r.name for r in dispatcher.sub_routers]

        assert names[-1] == "stale"

    def test_every_router_is_named_so_the_order_is_assertable(self, dispatcher):
        assert all(r.name for r in dispatcher.sub_routers)


class TestMiddlewareAndHooks:
    def test_connections_are_closed_once_per_update_before_filters(self, dispatcher):
        from apps.bot.middlewares import CloseOldConnectionsMiddleware

        registered = dispatcher.update.outer_middleware[:]

        assert any(isinstance(m, CloseOldConnectionsMiddleware) for m in registered)

    def test_the_error_handler_is_registered(self, dispatcher):
        assert dispatcher.errors.handlers

    async def test_the_error_handler_swallows_rather_than_reraises(self, caplog):
        event = MagicMock()
        event.exception = RuntimeError("boom")

        with caplog.at_level(logging.ERROR):
            result = await error_handler(event)

        assert result is None
        assert "Unhandled exception" in caplog.text


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
    receive_wagon_number, whose MENU_BUTTONS guard re-prompts, rather than
    wiping the half-filled form.
    """

    def test_flow_comes_before_entry(self, dispatcher):
        names = [r.name for r in dispatcher.sub_routers]

        assert names.index("defect_flow") < names.index("defect_entry")

    def test_flow_comes_after_start(self, dispatcher):
        """Link buttons keep working mid-flow, as they did under PTB."""
        names = [r.name for r in dispatcher.sub_routers]

        assert names.index("start") < names.index("defect_flow")

    def test_flow_comes_before_tasks(self, dispatcher):
        """1:1 with PTB: list pagination is inert while a defect is in progress."""
        names = [r.name for r in dispatcher.sub_routers]

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

        missing = {s.state for s in DefectSG.__states__} - covered
        assert not missing
