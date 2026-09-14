"""Tests for the message fallback.

The valuable one is the silent branch. Message handlers inside the defect flow
are filtered by content type — text for the wagon number, a photo for the photo
step — and the flow's own catch-all covers callbacks only. So a sticker sent
mid-form already falls through to this handler, and clearing the state there
would destroy a form the user spent minutes on.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.bot.handlers.common.stale import KNOWN_STATES, unhandled_message
from apps.bot.messages import BotMessages as M
from apps.bot.states import AiChatSG, DefectSG, SupportSG
from apps.bot.tests.builders import make_message


def _state(current: str | None) -> MagicMock:
    state = MagicMock()
    state.get_state = AsyncMock(return_value=current)
    state.clear = AsyncMock()
    return state


class TestKnownStates:
    def test_it_covers_every_group_in_the_states_module(self):
        expected = {
            name
            for group in (DefectSG, SupportSG, AiChatSG)
            for name in group.__all_states_names__
        }

        assert expected == KNOWN_STATES

    def test_it_is_not_empty(self):
        """The silent branch would never fire if the scan came back empty."""
        assert len(KNOWN_STATES) == 19


class TestInsideALiveFlow:
    @pytest.mark.parametrize(
        "state_name",
        [DefectSG.wagon_num.state, DefectSG.photo.state, AiChatSG.chatting.state],
    )
    async def test_stays_silent(self, state_name):
        message = make_message("a sticker, say")

        await unhandled_message(message, _state(state_name))

        message.answer.assert_not_called()

    async def test_leaves_the_form_standing(self):
        state = _state(DefectSG.desc.state)

        await unhandled_message(make_message("oops"), state)

        state.clear.assert_not_called()


class TestNothingIsWaiting:
    async def test_answers_when_there_is_no_state(self):
        message = make_message("hello?")

        await unhandled_message(message, _state(None))

        message.answer.assert_awaited_once_with(
            str(M.UNHANDLED_MESSAGE), parse_mode=M.PARSE_MODE
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
        assert message.answer.await_args.args[0] == str(M.UNHANDLED_MESSAGE)

    async def test_a_renamed_attribute_counts_too(self):
        state = _state("DefectSG:wagon_number")

        await unhandled_message(make_message("12345678"), state)

        state.clear.assert_awaited_once()
