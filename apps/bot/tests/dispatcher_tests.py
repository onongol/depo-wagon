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

        assert names.index("utility") > names.index("start")

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
