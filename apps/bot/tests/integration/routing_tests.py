"""Routing precedences, which were implicit in PTB's add_handler order.

Nothing here can be tested by calling a handler directly: what is under test is
which handler an update reaches, and whether it reaches one at all.
"""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.bot.callback_data import (
    CB_NOOP,
    DepartmentCB,
    TasksPageCB,
)
from apps.bot.constants import BTN_ASK, BTN_HELP, BTN_NEW_DEFECT, UD_AI_CHAT_LAST
from apps.bot.messages import BotMessages as M
from apps.bot.middlewares import AI_CHAT_TIMEOUT
from apps.bot.states import AiChatSG, DefectSG
from apps.bot.tests.integration.conftest import (
    make_callback_update,
    make_message_update,
)


@pytest.fixture
def employee():
    emp = MagicMock()
    emp.id = 7
    emp.full_name = "Bat Erdene"
    emp.role = "inspector"
    emp.get_role_display.return_value = "Inspector"
    return emp


class TestStaleTiers:
    async def test_a_spacer_is_answered_without_touching_the_message(
        self, dp, bot, session
    ):
        """A blank nav button must never wipe the list it sits in."""
        await dp.feed_update(bot, make_callback_update(CB_NOOP))

        assert session.calls("answerCallbackQuery")
        assert session.calls("editMessageText") == []

    async def test_a_spacer_stays_silent_even_if_it_stops_being_a_known_payload(
        self, dp, bot, session
    ):
        """Why the spacer gets its own handler rather than relying on tier two.

        CB_NOOP is in LITERALS today, so the silent unroutable tier would catch
        it anyway. Drop it from that set — a refactor easily could — and without
        the dedicated handler the tap would fall through to the loud tier and
        replace the employee list with "this button expired".
        """
        with patch("apps.bot.filters.callback.is_known_callback", return_value=False):
            await dp.feed_update(bot, make_callback_update(CB_NOOP))

        assert session.calls("answerCallbackQuery")
        assert session.calls("editMessageText") == []

    async def test_a_pre_migration_payload_gets_the_expired_reply(
        self, dp, bot, session
    ):
        """PTB put a bare UUID on the wire; those arrive here after cutover."""
        await dp.feed_update(bot, make_callback_update(uuid.uuid4().hex))

        edits = session.calls("editMessageText")
        assert len(edits) == 1
        assert edits[0].text == str(M.BUTTON_EXPIRED)

    async def test_schema_drift_gets_the_expired_reply(self, dp, bot, session):
        """Known prefix, wrong arity — must not vanish into a silent answer."""
        await dp.feed_update(bot, make_callback_update("dset:" + uuid.uuid4().hex))

        assert len(session.calls("editMessageText")) == 1

    async def test_a_known_payload_in_the_wrong_state_is_absorbed_silently(
        self, dp, bot, session
    ):
        await dp.feed_update(
            bot, make_callback_update(DepartmentCB(value="bogie").pack())
        )

        assert session.calls("answerCallbackQuery")
        assert session.calls("editMessageText") == []


class TestPrecedenceDuringTheDefectFlow:
    async def _enter_photo_step(self, dp, bot, state, employee):
        with patch(
            "apps.bot.handlers.defect.start.get_employee",
            AsyncMock(return_value=employee),
        ):
            await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await state.set_state(DefectSG.photo)

    async def test_a_tasks_page_tap_is_absorbed_mid_flow(
        self, dp, bot, session, state, employee
    ):
        """1:1 with PTB: the flow's catch-all claims it before the tasks router."""
        await self._enter_photo_step(dp, bot, state, employee)
        session.clear()

        await dp.feed_update(bot, make_callback_update(TasksPageCB(page=1).pack()))

        assert session.calls("answerCallbackQuery")
        assert session.calls("editMessageText") == []
        assert await state.get_state() == DefectSG.photo.state

    async def test_the_new_defect_button_does_not_restart_a_running_flow(
        self, dp, bot, state, employee
    ):
        """The flow router precedes the entry router, so the guard re-prompts."""
        with patch(
            "apps.bot.handlers.defect.start.get_employee",
            AsyncMock(return_value=employee),
        ):
            await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await dp.feed_update(bot, make_message_update(str(BTN_NEW_DEFECT)))

        assert await state.get_state() == DefectSG.wagon_num.state

    async def test_start_still_works_mid_flow_and_leaves_the_flow_standing(
        self, dp, bot, state, employee
    ):
        """start_router precedes the flow, matching PTB's registration order."""
        await self._enter_photo_step(dp, bot, state, employee)

        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.get_employee_by_telegram_id = AsyncMock(return_value=None)
            svc.get_connect_url = MagicMock(return_value="https://x/telegram/")
            await dp.feed_update(bot, make_message_update("/start", command=True))

        assert await state.get_state() == DefectSG.photo.state


class TestAiChatPrecedence:
    async def test_the_new_defect_button_leaves_the_ai_chat(
        self, dp, bot, state, employee
    ):
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(return_value=employee),
        ):
            await dp.feed_update(bot, make_message_update("/ask", command=True))
        assert await state.get_state() == AiChatSG.chatting.state

        with patch(
            "apps.bot.handlers.defect.start.get_employee",
            AsyncMock(return_value=employee),
        ):
            await dp.feed_update(bot, make_message_update(str(BTN_NEW_DEFECT)))

        assert await state.get_state() == DefectSG.wagon_num.state

    async def test_the_help_button_cancels_instead_of_showing_help(
        self, dp, bot, session, state, employee
    ):
        """utility_router comes after ai_chat, so the flow's fallback wins."""
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(return_value=employee),
        ):
            await dp.feed_update(bot, make_message_update("/ask", command=True))
        session.clear()

        await dp.feed_update(bot, make_message_update(str(BTN_HELP)))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [str(M.CANCELLED)]
        assert await state.get_state() is None

    async def test_an_expired_session_lets_the_button_through_to_help(
        self, dp, bot, session, state, employee
    ):
        """The lazy timeout must clear the state *and* release the update."""
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(return_value=employee),
        ):
            await dp.feed_update(bot, make_message_update("/ask", command=True))

        await state.update_data({UD_AI_CHAT_LAST: time.time() - AI_CHAT_TIMEOUT - 1})
        session.clear()

        await dp.feed_update(bot, make_message_update(str(BTN_HELP)))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [str(M.HELP_TEXT)]
        assert await state.get_state() is None

    async def test_the_ask_button_starts_a_session(self, dp, bot, state, employee):
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(return_value=employee),
        ):
            await dp.feed_update(bot, make_message_update(str(BTN_ASK)))

        assert await state.get_state() == AiChatSG.chatting.state


class TestUnroutedUpdates:
    async def test_a_stray_text_outside_every_flow_is_ignored(self, dp, bot, session):
        """No global text handler exists, and none should be introduced."""
        await dp.feed_update(bot, make_message_update("just talking"))

        assert session.requests == []
