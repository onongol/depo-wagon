"""Routing precedences, which were implicit in PTB's add_handler order.

Nothing here can be tested by calling a handler directly: what is under test is
which handler an update reaches, and whether it reaches one at all.
"""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import Chat, Message, Update, User
from django.test import override_settings

from apps.bot.callback_data import (
    CB_NOOP,
    ConfirmCB,
    DepartmentCB,
    LinkConfirmCB,
    TasksPageCB,
)
from apps.bot.constants import (
    BTN_ASK,
    BTN_HELP,
    BTN_NEW_DEFECT,
    UD_AI_CHAT_LAST,
    LinkStatus,
)
from apps.bot.dispatcher import _BOT_COMMANDS, make_dispatcher
from apps.bot.fsm import save_defect
from apps.bot.handlers.common.link_errors import get_link_error_message
from apps.bot.handlers.common.text import build_cancelled_text, build_help_text
from apps.bot.handlers.support.utils import remember_request
from apps.bot.keyboards.menu import MENU_TEXTS
from apps.bot.messages import BotMessages as M
from apps.bot.middlewares import AI_CHAT_TIMEOUT
from apps.bot.states import AiChatSG, DefectSG, SupportSG
from apps.bot.tests.integration.conftest import (
    CHAT_ID,
    USER_ID,
    as_employee,
    make_callback_update,
    make_message_update,
)
from apps.bot.user_data import DefectData

SUPPORT_CHAT_ID = "apps.bot.handlers.support.user_handlers.support_chat_id"


@pytest.fixture
def employee():
    emp = MagicMock()
    emp.id = 7
    emp.full_name = "Bat Erdene"
    emp.role = "inspector"
    emp.get_role_display.return_value = "Inspector"
    return emp


class TestTheUnfilteredFallback:
    """One catch-all at the end of the dispatcher, with the spacer ahead of it.

    Nothing asks whether a payload is one this build knows. A tap arrives here
    only after every registered filter declined it, and that is taken as proof
    the button is dead.
    """

    async def test_a_spacer_is_answered_without_touching_the_message(
        self, dp, bot, session
    ):
        """A blank nav button must never wipe the list it sits in."""
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
        """Known prefix, wrong arity — no filter matches, so the fallback does."""
        await dp.feed_update(bot, make_callback_update("dset:" + uuid.uuid4().hex))

        assert len(session.calls("editMessageText")) == 1

    async def test_a_current_payload_outside_its_flow_also_gets_it(
        self, dp, bot, session
    ):
        """The behaviour the old middle tier existed to avoid, now accepted.

        DepartmentCB is a shape this build still packs, but with no defect flow
        running its handler's state filter declines and nothing else wants it.
        A silent answer here would leave the user tapping a button that will
        never do anything, so the fallback speaks instead.
        """
        await dp.feed_update(
            bot, make_callback_update(DepartmentCB(value="bogie").pack())
        )

        edits = session.calls("editMessageText")
        assert len(edits) == 1
        assert edits[0].text == str(M.BUTTON_EXPIRED)


class TestPrecedenceDuringTheDefectFlow:
    async def _enter_photo_step(self, dp, bot, state, employee):
        with as_employee(employee):
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
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await dp.feed_update(bot, make_message_update(str(BTN_NEW_DEFECT)))

        assert await state.get_state() == DefectSG.wagon_num.state

    @pytest.fixture
    async def at_wagon_step(self, dp, bot, session, employee):
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        session.clear()

    @pytest.mark.usefixtures("at_wagon_step")
    @pytest.mark.parametrize("label", sorted(MENU_TEXTS))
    async def test_no_menu_label_is_read_as_a_wagon_number(
        self, dp, bot, session, state, label
    ):
        await dp.feed_update(bot, make_message_update(label))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [str(M.WAGON_NUM_PROMPT)]
        assert await state.get_state() == DefectSG.wagon_num.state

    async def test_start_still_works_mid_flow_and_leaves_the_flow_standing(
        self, dp, bot, state, employee
    ):
        """start_router precedes the flow, matching PTB's registration order."""
        await self._enter_photo_step(dp, bot, state, employee)

        with (
            as_employee(None),
            patch("apps.bot.handlers.common.start.services") as svc,
        ):
            svc.get_connect_url = MagicMock(return_value="https://x/telegram/")
            await dp.feed_update(bot, make_message_update("/start", command=True))

        assert await state.get_state() == DefectSG.photo.state


class TestAiChatPrecedence:
    async def test_the_new_defect_button_leaves_the_ai_chat(
        self, dp, bot, state, employee
    ):
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/ask", command=True))
        assert await state.get_state() == AiChatSG.chatting.state

        with as_employee(employee):
            await dp.feed_update(bot, make_message_update(str(BTN_NEW_DEFECT)))

        assert await state.get_state() == DefectSG.wagon_num.state

    async def test_the_help_button_cancels_instead_of_showing_help(
        self, dp, bot, session, state, employee
    ):
        """help_router comes after ai_chat, so the flow's fallback wins."""
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/ask", command=True))
        session.clear()

        await dp.feed_update(bot, make_message_update(str(BTN_HELP)))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_cancelled_text().render()[0]]
        assert await state.get_state() is None

    async def test_an_expired_session_lets_the_button_through_to_help(
        self, dp, bot, session, state, employee
    ):
        """The lazy timeout must clear the state *and* release the update."""
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/ask", command=True))

        await state.update_data({UD_AI_CHAT_LAST: time.time() - AI_CHAT_TIMEOUT - 1})
        session.clear()

        await dp.feed_update(bot, make_message_update(str(BTN_HELP)))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_help_text().render()[0]]
        assert await state.get_state() is None

    async def test_a_router_ahead_of_ai_chat_still_expires_the_session(
        self, dp, bot, state, employee
    ):
        """tasks sits before ai_chat, so only a global check catches this one."""
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/ask", command=True))
        await state.update_data({UD_AI_CHAT_LAST: time.time() - AI_CHAT_TIMEOUT - 1})

        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/my_tasks", command=True))

        assert await state.get_state() is None

    async def test_a_question_in_the_session_reaches_the_assistant(
        self, dp, bot, session, state, employee
    ):
        """Free text mid-session routes past every earlier router to ai_chat_receive."""
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/ask", command=True))
        session.clear()

        answer = AsyncMock(return_value="Tolerance is 3 mm.")
        with (
            as_employee(employee),
            patch("apps.bot.handlers.ai_chat.receive.answer_question", answer),
        ):
            await dp.feed_update(bot, make_message_update("What is the tolerance?"))

        assert answer.await_args.args[0] == "What is the tolerance?"
        assert [m.text for m in session.calls("editMessageText")] == [
            "Tolerance is 3 mm."
        ]
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_a_session_ends_once_the_employee_is_gone(
        self, dp, bot, session, state, employee
    ):
        """The idle timeout never fires while the user keeps typing."""
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/ask", command=True))
        session.clear()

        answer = AsyncMock()
        with (
            as_employee(None),
            patch("apps.bot.handlers.ai_chat.receive.answer_question", answer),
        ):
            await dp.feed_update(bot, make_message_update("What is the tolerance?"))

        answer.assert_not_awaited()
        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [str(M.NOT_REGISTERED)]
        assert await state.get_state() is None

    async def test_the_help_button_gets_help_eleven_minutes_on(
        self, dp, bot, session, state, employee
    ):
        """The same fall-through, but expiring the stamp the middleware wrote itself."""
        from apps.bot.middlewares import ai_chat_timeout

        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/ask", command=True))

        assert (await state.get_data())[UD_AI_CHAT_LAST] > 0
        session.clear()

        eleven_minutes_on = MagicMock(time=lambda: time.time() + 660)
        with (
            as_employee(employee),
            patch.object(ai_chat_timeout, "time", eleven_minutes_on),
        ):
            await dp.feed_update(bot, make_message_update(str(BTN_HELP)))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_help_text().render()[0]]
        assert await state.get_state() is None

    async def test_the_ask_button_starts_a_session(self, dp, bot, state, employee):
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update(str(BTN_ASK)))

        assert await state.get_state() == AiChatSG.chatting.state


class TestSupportPrecedence:
    """support sits ahead of ai_chat and help, whose buttons would reach it."""

    @pytest.mark.parametrize("button", [BTN_ASK, BTN_HELP])
    async def test_a_menu_button_cancels_instead_of_being_relayed(
        self, dp, bot, session, state, button
    ):
        await state.set_state(SupportSG.message)

        with patch(SUPPORT_CHAT_ID, return_value=-100):
            await dp.feed_update(bot, make_message_update(str(button)))

        sent = session.calls("sendMessage")
        cancelled = build_cancelled_text().render()[0]
        assert [(m.chat_id, m.text) for m in sent] == [(CHAT_ID, cancelled)]
        assert await state.get_state() is None

    async def test_a_question_is_still_relayed(self, dp, bot, session, state, employee):
        await state.set_state(SupportSG.message)

        with as_employee(employee), patch(SUPPORT_CHAT_ID, return_value=-100):
            await dp.feed_update(bot, make_message_update("The printer is broken"))

        assert session.calls("sendMessage")[0].chat_id == -100

    async def test_a_reply_in_the_support_group_reaches_the_user(
        self, bot, session, storage
    ):
        """The one handler meant for a group, so PRIVATE_CHAT must not cover it."""
        group_id = -1001234567890
        await remember_request(4242, USER_ID)
        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=str(group_id)):
            dp = make_dispatcher(storage, SimpleEventIsolation())

        group = Chat(id=group_id, type="supergroup")
        operator = User(id=999, is_bot=False, first_name="Operator")
        reply = Message(
            message_id=5000,
            date=0,
            chat=group,
            from_user=operator,
            text="Fixed",
            reply_to_message=Message(
                message_id=4242, date=0, chat=group, from_user=operator
            ),
        )
        await dp.feed_update(bot, Update(update_id=90000, message=reply))

        assert session.calls("sendMessage")[0].chat_id == USER_ID


class TestUnroutedUpdates:
    """The stale router now answers messages too.

    It used to assert the opposite — that a stray text is met with silence and
    no global handler should be introduced. That held while every silence had a
    prompt still on screen behind it. It stopped holding once the FSM took a
    TTL: the key expires under a user who is mid-form, and from then on the
    step that asked the question no longer exists to answer them.
    """

    async def test_a_stray_text_outside_every_flow_is_answered(self, dp, bot, session):
        await dp.feed_update(bot, make_message_update("just talking"))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [str(M.UNHANDLED_MESSAGE)]

    async def test_an_unknown_command_is_answered_too(self, dp, bot, session):
        await dp.feed_update(bot, make_message_update("/nope", command=True))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [str(M.UNHANDLED_MESSAGE)]

    async def test_a_known_command_still_wins(self, dp, bot, session):
        """The fallback is last, so /help must never reach it."""
        await dp.feed_update(bot, make_message_update("/help", command=True))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_help_text().render()[0]]

    async def test_a_group_chat_is_left_alone(self, dp, bot, session):
        """The support group carries traffic this bot must not answer."""
        await dp.feed_update(
            bot, make_message_update("chatter", chat_type="supergroup")
        )

        assert session.requests == []

    @pytest.mark.parametrize(
        "text", [f"/{c}" for c, _d in _BOT_COMMANDS] + sorted(MENU_TEXTS)
    )
    async def test_no_entry_point_answers_in_a_group(
        self, dp, bot, session, employee, text
    ):
        """A defect list, a name or an AI answer would be read by the whole group."""
        update = make_message_update(
            text, command=text.startswith("/"), chat_type="supergroup"
        )

        with as_employee(employee) as lookup:
            await dp.feed_update(bot, update)

        assert session.requests == []
        lookup.assert_not_awaited()

    async def test_the_wrong_content_type_mid_form_stays_silent(
        self, dp, bot, session, state, employee
    ):
        """The photo step asks for a photo. Typing at it must not end the form."""
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update(str(BTN_NEW_DEFECT)))
        await state.set_state(DefectSG.photo)
        session.clear()

        await dp.feed_update(bot, make_message_update("not a photo"))

        assert session.requests == []
        assert await state.get_state() == DefectSG.photo.state


class TestAFailedEmployeeLookup:
    """The middleware raises; the reply comes from error_handler, as for any fault."""

    LOOKUP = "apps.bot.middlewares.employee.services.get_employee_by_telegram_id"

    async def test_a_message_is_told_the_session_failed(self, dp, bot, session):
        with patch(self.LOOKUP, AsyncMock(side_effect=RuntimeError("db down"))):
            await dp.feed_update(bot, make_message_update("/my_tasks", command=True))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [str(M.SESSION_ERROR)]

    async def test_a_callback_is_answered_and_told(self, dp, bot, session):
        with patch(self.LOOKUP, AsyncMock(side_effect=RuntimeError("db down"))):
            await dp.feed_update(bot, make_callback_update(TasksPageCB(page=2).pack()))

        assert session.method_names() == ["answerCallbackQuery", "sendMessage"]
        assert session.calls("sendMessage")[0].text == str(M.SESSION_ERROR)


class TestAFailedAccountLink:
    """The link handlers catch nothing themselves; error_handler answers for them."""

    async def test_the_chat_is_told_the_session_failed(self, dp, bot, session):
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                side_effect=ConnectionError("redis down")
            )
            await dp.feed_update(
                bot, make_message_update("/start sometoken", command=True)
            )

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [str(M.SESSION_ERROR)]

    async def test_a_confirm_tap_is_told_the_session_failed(self, dp, bot, session):
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.complete_telegram_link = AsyncMock(
                side_effect=ConnectionError("redis down")
            )
            await dp.feed_update(
                bot, make_callback_update(LinkConfirmCB(employee_id=42).pack())
            )

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [str(M.SESSION_ERROR)]
        assert session.calls("editMessageText") == []


class TestHandlersThatNeedNoEmployee:
    """The lookup follows the handler's signature, so these must not trigger it."""

    async def test_cancelling_at_confirm_does_not_look_up_the_employee(
        self, dp, bot, session, state
    ):
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(DefectSG.confirm)

        with as_employee(None) as lookup:
            await dp.feed_update(
                bot, make_callback_update(ConfirmCB(confirmed=False).pack())
            )

        lookup.assert_not_awaited()
        assert await state.get_state() is None
        assert session.calls("editMessageText")[0].text == str(M.DEFECT_CANCELLED)

    async def test_a_deep_link_does_not_look_up_the_employee(self, dp, bot, session):
        with (
            as_employee(None) as lookup,
            patch("apps.bot.handlers.common.start.services") as svc,
        ):
            svc.resolve_link_token = AsyncMock(
                return_value=(None, LinkStatus.INVALID_TOKEN)
            )
            await dp.feed_update(
                bot, make_message_update("/start sometoken", command=True)
            )

        lookup.assert_not_awaited()
        assert svc.resolve_link_token.await_args.args == ("sometoken",)
        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [get_link_error_message(LinkStatus.INVALID_TOKEN).render()[0]]
