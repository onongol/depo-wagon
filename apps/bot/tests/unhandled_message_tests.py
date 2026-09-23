"""Tests for the message fallback.

The silent branch lives in the router, not here: ~StateFilter(*ALL_GROUPS)
keeps a sticker sent mid-form from ever reaching the handler, and
routing_tests covers that walk. What stays testable directly is the handler
itself and the completeness of ALL_GROUPS — a group left out of it would have
its forms cleared by the first wrong-content message.
"""

import inspect
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.state import StatesGroup

from apps.bot import states
from apps.bot.handlers.common.stale import unhandled_message
from apps.bot.handlers.common.text import build_unhandled_message_text
from apps.bot.states import ALL_GROUPS
from apps.bot.tests.builders import make_message


def _state(current: str | None) -> MagicMock:
    state = MagicMock()
    state.get_state = AsyncMock(return_value=current)
    state.clear = AsyncMock()
    return state


class TestAllGroups:
    def test_lists_every_group_in_the_states_module(self):
        declared = {
            group
            for _, group in inspect.getmembers(states, inspect.isclass)
            if issubclass(group, StatesGroup) and group is not StatesGroup
        }

        assert declared == set(ALL_GROUPS)

    def test_the_scan_finds_something(self):
        """Guards the test above against comparing two empty sets."""
        assert len(ALL_GROUPS) == 3


class TestNothingIsWaiting:
    async def test_answers_when_there_is_no_state(self):
        message = make_message("hello?")

        await unhandled_message(message, _state(None))

        message.answer.assert_awaited_once_with(
            **build_unhandled_message_text().as_kwargs()
        )

    async def test_has_nothing_to_clear_when_there_is_no_state(self):
        state = _state(None)

        await unhandled_message(make_message("hello?"), state)

        state.clear.assert_not_called()


class TestAStateThisBuildDoesNotKnow:
    async def test_clears_it_and_says_so(self):
        """What a renamed StatesGroup leaves behind in Redis."""
        message = make_message("12345678")
        state = _state("RetiredSG:wagon_num")

        await unhandled_message(message, state)

        state.clear.assert_awaited_once()
        sent = message.answer.await_args.kwargs
        assert sent == build_unhandled_message_text().as_kwargs()

    async def test_a_renamed_attribute_counts_too(self):
        state = _state("DefectSG:wagon_number")

        await unhandled_message(make_message("12345678"), state)

        state.clear.assert_awaited_once()
