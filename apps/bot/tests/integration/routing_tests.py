"""Routing precedences, which were implicit in PTB's add_handler order.

Nothing here can be tested by calling a handler directly: what is under test is
which handler an update reaches, and whether it reaches one at all.
"""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Router
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import Chat, Message, Update, User
from django.db import OperationalError
from django.test import override_settings

from apps.bot.callback_data import (
    CB_DEFECT_CONTINUE,
    CB_DEFECT_RESTART,
    CB_DESC_SKIP,
    CB_LINK_CANCEL,
    CB_NOOP,
    CB_PHOTO_SKIP,
    ConfirmCB,
    DefectCardCB,
    DepartmentCB,
    LinkConfirmCB,
    TasksPageCB,
)
from apps.bot.constants import (
    BTN_ASK,
    BTN_HELP,
    BTN_NEW_DEFECT,
    BTN_OPEN_DEFECTS,
    UD_AI_CHAT_LAST,
    UD_EDITING,
    UD_SCREEN,
    LinkStatus,
)
from apps.bot.dispatcher import _BOT_COMMANDS, _routers, make_dispatcher
from apps.bot.errors import build_session_error_text
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.common.text import (
    build_button_expired_text,
    build_cancelled_text,
    build_help_text,
    build_unhandled_message_text,
)
from apps.bot.handlers.defect.scenes import DEFECT_SCENES
from apps.bot.handlers.defect.text import (
    build_ask_department_text,
    build_ask_more_photos_text,
    build_ask_wagon_text,
    build_defect_cancelled_text,
    build_defect_continued_text,
    build_defect_in_progress_text,
    build_edit_description_text,
    build_stray_input_text,
)
from apps.bot.handlers.defect.wagon import WagonScene
from apps.bot.handlers.start.link_errors import get_link_error_message
from apps.bot.handlers.start.text import build_link_cancelled_text
from apps.bot.handlers.support.utils import remember_request
from apps.bot.handlers.tasks.text import build_no_tasks_text
from apps.bot.keyboards.common import done_keyboard, skip_keyboard, with_step_buttons
from apps.bot.keyboards.defect import defect_in_progress_keyboard, department_keyboard
from apps.bot.keyboards.menu import MENU_TEXTS, main_menu_keyboard
from apps.bot.middlewares import AI_CHAT_TIMEOUT
from apps.bot.states import AiChatSG, DefectSG, SupportSG
from apps.bot.tests.integration.conftest import (
    CHAT_ID,
    USER_ID,
    as_employee,
    make_callback_update,
    make_message_update,
    make_photo_update,
)
from apps.bot.user_data import DefectData, MeasurementEntry, PhotoEntry
from apps.bot.utils.unregistered import build_not_registered_text
from apps.core.constants import Department

RESP_SERVICES = "apps.bot.handlers.defect.responsible_employee.list.services"
SUPPORT_CHAT_ID = "apps.bot.handlers.support.request.support_chat_id"
TASKS_COUNT = "apps.bot.handlers.tasks.render.services.get_open_defects_count"
TASKS_PAGE = "apps.bot.handlers.tasks.render.services.get_open_defects"


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
        assert edits[0].text == build_button_expired_text().render()[0]

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
        assert edits[0].text == build_button_expired_text().render()[0]


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

    FORM = DefectData(
        wagon_id=3,
        wagon_number="80035668",
        department=Department.BOGIE.value,
        department_label="Bogie",
        defect_type_label="Crack",
        severity_label="High",
        current_measurement=MeasurementEntry(
            dimension="depth", dimension_label="Depth"
        ),
    )

    @pytest.fixture
    async def stored_form(self, state):
        await save_defect(state, self.FORM)

    @pytest.mark.usefixtures("stored_form")
    @pytest.mark.parametrize(
        "label",
        [
            *sorted(MENU_TEXTS - {str(BTN_NEW_DEFECT)}),
            *("/start", "/my_tasks", "/ask", "/support", "/help"),
        ],
    )
    @pytest.mark.parametrize(
        "step",
        [s for s in DefectSG.__states__ if s != DefectSG.saving],
        ids=lambda s: s.state,
    )
    async def test_a_menu_button_shows_the_step_again(
        self, dp, bot, state, step, label
    ):
        """Never an answer at a text step, and never a way out: /cancel is that.

        Nor taken off the chat: only a step's answers are. The commands too.
        """
        await state.set_state(step)
        before = await state.get_data()
        scene = next(s for s in DEFECT_SCENES if s.__scene_config__.state == step.state)

        with patch(RESP_SERVICES) as svc:
            svc.count_department_employees = AsyncMock(return_value=0)
            svc.get_department_employees = AsyncMock(return_value=[])
            update = make_message_update(label, command=label.startswith("/"))
            await dp.feed_update(bot, update)
            after = await state.get_data()
            expected, _ = await scene.draw(await load_defect(state), after)

        (sent,) = bot.session.calls("sendMessage")
        assert sent.text == expected.render()[0]
        assert bot.session.calls("deleteMessage") == []
        assert await state.get_state() == step.state
        # The screen drawn is the only thing stored
        assert {k: v for k, v in after.items() if k != UD_SCREEN} == before

    @pytest.mark.usefixtures("stored_form")
    async def test_at_the_wagon_step_it_asks_for_the_number_again(self, dp, bot, state):
        """A Scene: retake() draws the screen entering it drew, with its Cancel."""
        await state.set_state(DefectSG.wagon_num)

        await dp.feed_update(bot, make_message_update(str(BTN_OPEN_DEFECTS)))

        (sent,) = bot.session.calls("sendMessage")
        assert sent.text.endswith(build_ask_wagon_text().render()[0])
        assert sent.reply_markup == with_step_buttons(None, back=False)

    async def test_a_deep_link_mid_flow_still_reaches_the_link_handler(
        self, dp, bot, state, employee
    ):
        """Only a bare /start is left to the form; linking comes from the web app."""
        await self._enter_photo_step(dp, bot, state, employee)

        with patch("apps.bot.handlers.start.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                return_value=(None, LinkStatus.INVALID_TOKEN)
            )
            await dp.feed_update(
                bot, make_message_update("/start sometoken", command=True)
            )

        svc.resolve_link_token.assert_awaited_once_with("sometoken")
        assert await state.get_state() == DefectSG.photo.state

    async def test_a_link_button_mid_flow_reaches_the_link_handler(
        self, dp, bot, state, employee
    ):
        """start precedes the flow, whose catch-all would swallow the tap."""
        await self._enter_photo_step(dp, bot, state, employee)

        with patch("apps.bot.handlers.start.start.services") as svc:
            svc.complete_telegram_link = AsyncMock(
                return_value=(None, LinkStatus.OFFER_EXPIRED)
            )
            await dp.feed_update(
                bot, make_callback_update(LinkConfirmCB(employee_id=7).pack())
            )

        svc.complete_telegram_link.assert_awaited_once()

    async def test_cancel_mid_flow_is_the_global_cancel(
        self, dp, bot, session, state, employee
    ):
        """cancel precedes the flow, so /cancel ends everything, not just the form."""
        await self._enter_photo_step(dp, bot, state, employee)
        await state.update_data({UD_AI_CHAT_LAST: 1.0})
        session.clear()

        await dp.feed_update(bot, make_message_update("/cancel", command=True))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_cancelled_text().render()[0]]
        assert await state.get_state() is None
        assert await state.get_data() == {}


class TestNewDefectDuringARunningForm:
    """Asked at every step, not only where a text handler guards menu labels."""

    WAGON = "80035668"

    @pytest.fixture
    async def form(self, state):
        await save_defect(state, DefectData(wagon_id=3, wagon_number=self.WAGON))
        await state.update_data({UD_EDITING: True})

    @pytest.mark.usefixtures("form")
    @pytest.mark.parametrize(
        "step",
        [
            DefectSG.wagon_num,
            DefectSG.department,
            DefectSG.photo,
            DefectSG.desc,
            DefectSG.confirm,
            DefectSG.employee_verdict,
        ],
        ids=lambda s: s.state,
    )
    @pytest.mark.parametrize(
        "text", ["/new_defect", str(BTN_NEW_DEFECT)], ids=["command", "button"]
    )
    async def test_the_form_is_kept_and_the_user_asked(
        self, dp, bot, state, step, text
    ):
        """No employee: reaching the entry instead would refuse the chat."""
        await state.set_state(step)
        update = make_message_update(text, command=text.startswith("/"))

        with as_employee(None):
            await dp.feed_update(bot, update)

        (sent,) = bot.session.calls("sendMessage")
        assert sent.text.endswith(build_defect_in_progress_text().render()[0])
        assert sent.reply_markup == defect_in_progress_keyboard()
        assert bot.session.calls("deleteMessage") == []
        assert await state.get_state() == step.state
        assert (await load_defect(state)).wagon_number == self.WAGON

    @pytest.mark.usefixtures("form")
    async def test_continue_shows_the_step_again(self, dp, bot, session, state):
        await state.set_state(DefectSG.desc)

        await dp.feed_update(bot, make_callback_update(CB_DEFECT_CONTINUE))

        (edit,) = session.calls("editMessageText")
        assert edit.text.endswith(build_edit_description_text().render()[0])
        assert edit.reply_markup == with_step_buttons(
            skip_keyboard(CB_DESC_SKIP), back=True
        )
        assert await state.get_state() == DefectSG.desc.state
        assert (await load_defect(state)).wagon_number == self.WAGON

    @pytest.fixture
    async def full_form(self, state):
        await save_defect(
            state,
            DefectData(
                wagon_id=3,
                wagon_number=self.WAGON,
                department=Department.BOGIE.value,
                department_label="Bogie",
                defect_type_label="Crack",
                severity_label="High",
                current_measurement=MeasurementEntry(
                    dimension="depth", dimension_label="Depth"
                ),
            ),
        )

    @pytest.mark.usefixtures("full_form")
    @pytest.mark.parametrize(
        "step",
        [s for s in DefectSG.__states__ if s != DefectSG.saving],
        ids=lambda s: s.state,
    )
    async def test_every_step_has_a_screen_to_return_to(
        self, dp, bot, session, state, step
    ):
        await state.set_state(step)

        with patch(RESP_SERVICES) as svc:
            svc.count_department_employees = AsyncMock(return_value=0)
            svc.get_department_employees = AsyncMock(return_value=[])
            await dp.feed_update(bot, make_callback_update(CB_DEFECT_CONTINUE))

        (edit,) = session.calls("editMessageText")
        assert edit.text != build_defect_continued_text().render()[0]
        assert await state.get_state() == step.state

    @pytest.mark.usefixtures("form")
    async def test_the_department_step_shows_the_wagon_as_the_step_did(
        self, dp, bot, session, state
    ):
        await state.set_state(DefectSG.department)

        await dp.feed_update(bot, make_callback_update(CB_DEFECT_CONTINUE))

        (edit,) = session.calls("editMessageText")
        assert f"🚃 Wagon: {self.WAGON}" in edit.text
        assert edit.text.endswith(build_ask_department_text().render()[0])
        assert edit.reply_markup == with_step_buttons(department_keyboard(), back=True)

    async def test_the_photo_step_offers_done_once_a_photo_is_in(
        self, dp, bot, session, state
    ):
        photo = PhotoEntry(file_id="f", message_id=1)
        await save_defect(state, DefectData(photos=[photo, photo]))
        await state.set_state(DefectSG.photo)

        await dp.feed_update(bot, make_callback_update(CB_DEFECT_CONTINUE))

        (edit,) = session.calls("editMessageText")
        assert "📸 Photos: 2" in edit.text
        assert edit.text.endswith(build_ask_more_photos_text().render()[0])
        assert edit.reply_markup == with_step_buttons(
            done_keyboard(CB_PHOTO_SKIP), back=True
        )

    @pytest.mark.usefixtures("form")
    async def test_continue_while_saving_just_says_carry_on(
        self, dp, bot, session, state
    ):
        await state.set_state(DefectSG.saving)

        await dp.feed_update(bot, make_callback_update(CB_DEFECT_CONTINUE))

        edits = [e.text for e in session.calls("editMessageText")]
        assert edits == [build_defect_continued_text().render()[0]]

    @pytest.mark.usefixtures("form")
    @pytest.mark.parametrize("label", [str(BTN_OPEN_DEFECTS), "/help"])
    async def test_a_menu_button_while_saving_just_says_carry_on(
        self, dp, bot, session, state, label
    ):
        """A save that died half-way has no screen to show again."""
        await state.set_state(DefectSG.saving)

        await dp.feed_update(
            bot, make_message_update(label, command=label.startswith("/"))
        )

        (sent,) = session.calls("sendMessage")
        assert sent.text == build_defect_continued_text().render()[0]
        assert await state.get_state() == DefectSG.saving.state

    @pytest.mark.usefixtures("form")
    @pytest.mark.parametrize(
        "step", [DefectSG.saving, DefectSG.wagon_num], ids=["saving", "step"]
    )
    async def test_start_over_opens_a_blank_form(self, dp, bot, session, state, step):
        """UD_EDITING surviving would send the next wagon number to the summary."""
        await state.set_state(step)

        await dp.feed_update(bot, make_callback_update(CB_DEFECT_RESTART))

        (edit,) = session.calls("editMessageText")
        blank, _ = await WagonScene.draw(DefectData(), {})
        assert edit.text == blank.render()[0]
        assert await state.get_state() == DefectSG.wagon_num.state
        assert await load_defect(state) == DefectData()
        assert UD_EDITING not in await state.get_data()


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
        """start sits before ai_chat and keeps the state, so only a global check can."""
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/ask", command=True))
        await state.update_data({UD_AI_CHAT_LAST: time.time() - AI_CHAT_TIMEOUT - 1})

        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/start", command=True))

        assert await state.get_state() is None

    async def test_start_mid_session_leaves_the_chat_standing(
        self, dp, bot, state, employee
    ):
        """The control for the test above: without the timeout, /start keeps it."""
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update("/ask", command=True))
            await dp.feed_update(bot, make_message_update("/start", command=True))

        assert await state.get_state() == AiChatSG.chatting.state

    @pytest.mark.parametrize("flow", [AiChatSG.chatting, SupportSG.message])
    async def test_open_defects_leaves_the_flow_and_shows_the_list(
        self, dp, bot, state, employee, flow
    ):
        """Like New Defect: the next text must not go to the assistant or support."""
        await state.set_state(flow)

        with (
            as_employee(employee),
            patch(SUPPORT_CHAT_ID, return_value=-100),
            patch(TASKS_COUNT, AsyncMock(return_value=0)),
            patch(TASKS_PAGE, AsyncMock(return_value=[])),
        ):
            await dp.feed_update(bot, make_message_update(str(BTN_OPEN_DEFECTS)))

        assert await state.get_state() is None
        sent = [m.text for m in bot.session.calls("sendMessage")]
        assert sent == [build_no_tasks_text().render()[0]]

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
        assert sent == [build_not_registered_text().render()[0]]
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
        assert sent == [build_unhandled_message_text().render()[0]]

    async def test_an_unknown_command_is_answered_too(self, dp, bot, session):
        await dp.feed_update(bot, make_message_update("/nope", command=True))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_unhandled_message_text().render()[0]]

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

    @pytest.mark.parametrize(
        "data",
        [
            LinkConfirmCB(employee_id=42).pack(),
            CB_LINK_CANCEL,
            DefectCardCB(defect_id=uuid.uuid4(), page=0).pack(),
            TasksPageCB(page=1).pack(),
            CB_NOOP,
            "garbage",
        ],
        ids=["link", "link_cancel", "card", "page", "noop", "stale"],
    )
    @pytest.mark.parametrize("inaccessible", [False, True])
    async def test_no_button_answers_in_a_group(
        self, dp, bot, employee, data, inaccessible
    ):
        """Only a forged tap lands there; answering it would edit the group's message."""
        update = make_callback_update(
            data, inaccessible=inaccessible, chat_type="supergroup"
        )

        with as_employee(employee) as lookup:
            await dp.feed_update(bot, update)

        assert bot.session.requests == []
        lookup.assert_not_awaited()

    async def test_the_wrong_content_type_mid_form_gets_a_hint_on_the_screen(
        self, dp, bot, session, state, employee
    ):
        """The photo step asks for a photo. Typing at it must not end the form.

        Not an answer, so it stays; the screen goes under it and says so.
        """
        with as_employee(employee):
            await dp.feed_update(bot, make_message_update(str(BTN_NEW_DEFECT)))
        await state.set_state(DefectSG.photo)
        _, old_screen = (await state.get_data())[UD_SCREEN]
        session.clear()

        await dp.feed_update(bot, make_message_update("not a photo"))

        (sent,) = session.calls("sendMessage")
        assert build_stray_input_text().render()[0] in sent.text
        assert [d.message_id for d in session.calls("deleteMessage")] == [old_screen]
        assert await state.get_state() == DefectSG.photo.state

    async def test_a_stray_photo_mid_form_stays_and_gets_the_screen_under_it(
        self, dp, bot, session, state
    ):
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(DefectSG.desc)

        await dp.feed_update(bot, make_photo_update("stray"))

        (sent,) = session.calls("sendMessage")
        assert build_stray_input_text().render()[0] in sent.text
        assert (await load_defect(state)).photos == []
        assert await state.get_state() == DefectSG.desc.state

    @pytest.mark.parametrize(
        "known", [SupportSG.message, AiChatSG.chatting], ids=lambda s: s.state
    )
    async def test_every_other_group_keeps_its_state_through_a_stray_photo(
        self, dp, bot, session, state, known
    ):
        """One state from each of the other groups; each step there asks for text."""
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(known)

        await dp.feed_update(bot, make_photo_update("stray"))

        assert session.requests == []
        assert await state.get_state() == known.state

    async def test_a_state_left_by_an_older_build_is_cleared_and_answered(
        self, dp, bot, session, state
    ):
        await state.set_state("RetiredSG:wagon_num")

        await dp.feed_update(bot, make_message_update("12345678"))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_unhandled_message_text().render()[0]]
        assert await state.get_state() is None


class TestAPrivateRouterNeedsNoChatFilter:
    """The chat type is filtered once, on the private tree, for every router in it."""

    @pytest.fixture
    def seen(self):
        return []

    @pytest.fixture
    def dp(self, storage, seen):
        """The real tree with an unfiltered catch-all first in line."""

        async def spy(event) -> None:
            seen.append(event)

        def with_spy():
            extra = Router(name="unfiltered")
            extra.message.register(spy)
            extra.callback_query.register(spy)
            return [extra, *_routers()]

        with patch("apps.bot.dispatcher._routers", with_spy):
            return make_dispatcher(storage, SimpleEventIsolation())

    async def test_a_group_message_never_reaches_it(self, dp, bot, seen):
        await dp.feed_update(bot, make_message_update("hi", chat_type="supergroup"))

        assert seen == []

    async def test_a_group_tap_never_reaches_it(self, dp, bot, seen):
        await dp.feed_update(bot, make_callback_update("x", chat_type="supergroup"))

        assert seen == []

    async def test_a_private_chat_does(self, dp, bot, seen):
        """Keeps the two above from passing on a spy that was never wired."""
        await dp.feed_update(bot, make_message_update("hi"))
        await dp.feed_update(bot, make_callback_update("x"))

        assert len(seen) == 2


class TestAFailingOuterMiddleware:
    """ErrorsMiddleware is aiogram's first outer middleware, so it wraps ours too."""

    @pytest.fixture
    def _no_swallowed_crash(self):
        """These tests break a middleware on purpose."""
        yield

    async def test_fsm_storage_down(self, dp, bot, session, storage):
        """aiogram's own FSMContextMiddleware reads the state before any router."""
        with patch.object(
            storage, "get_state", AsyncMock(side_effect=ConnectionError("redis down"))
        ):
            await dp.feed_update(bot, make_message_update("/help", command=True))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_session_error_text().render()[0]]

    async def test_the_ai_chat_timeout_check_failing(self, dp, bot, session, state):
        await state.set_state(AiChatSG.chatting)

        with patch.object(
            state.storage,
            "get_data",
            AsyncMock(side_effect=ConnectionError("redis down")),
        ):
            await dp.feed_update(bot, make_message_update("/help", command=True))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_session_error_text().render()[0]]

    async def test_connection_cleanup_failing_after_the_handler_answered(
        self, dp, bot, session
    ):
        """The cleanup runs in finally, so the user is served and then told it failed."""
        with patch(
            "apps.bot.middlewares.db.close_old_connections",
            side_effect=OperationalError("db gone"),
        ):
            await dp.feed_update(bot, make_message_update("/help", command=True))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [
            build_help_text().render()[0],
            build_session_error_text().render()[0],
        ]


class TestAFailedEmployeeLookup:
    """The middleware raises; the reply comes from error_handler, as for any fault."""

    @pytest.fixture
    def _no_swallowed_crash(self):
        """These tests break a handler on purpose."""
        yield

    LOOKUP = "apps.bot.middlewares.employee.services.get_employee_by_telegram_id"

    async def test_a_message_is_told_the_session_failed(self, dp, bot, session):
        with patch(self.LOOKUP, AsyncMock(side_effect=RuntimeError("db down"))):
            await dp.feed_update(bot, make_message_update("/my_tasks", command=True))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_session_error_text().render()[0]]

    async def test_a_callback_is_answered_and_told(self, dp, bot, session):
        with patch(self.LOOKUP, AsyncMock(side_effect=RuntimeError("db down"))):
            await dp.feed_update(bot, make_callback_update(TasksPageCB(page=2).pack()))

        assert session.method_names() == ["answerCallbackQuery", "sendMessage"]
        assert (
            session.calls("sendMessage")[0].text
            == build_session_error_text().render()[0]
        )


class TestAButtonOnAnInaccessibleMessage:
    """No edit methods of its own: the bot edits it by id, or sends anew if refused."""

    DELETED = "Bad Request: message to edit not found"

    async def test_cancelling_a_link_edits_it_by_id(self, dp, bot, session):
        await dp.feed_update(
            bot, make_callback_update(CB_LINK_CANCEL, inaccessible=True)
        )

        edits = [m.text for m in session.calls("editMessageText")]
        assert edits == [build_link_cancelled_text().render()[0]]
        assert session.calls("sendMessage") == []

    async def test_a_deleted_message_gets_the_reply_anew(self, dp, bot, session):
        session.refuse("editMessageText", self.DELETED)

        await dp.feed_update(
            bot, make_callback_update(CB_LINK_CANCEL, inaccessible=True)
        )

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_link_cancelled_text().render()[0]]

    async def test_an_expired_confirmation_still_says_so(self, dp, bot, session):
        session.refuse("editMessageText", self.DELETED)
        callback_data = LinkConfirmCB(employee_id=42).pack()

        await dp.feed_update(
            bot, make_callback_update(callback_data, inaccessible=True)
        )

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [get_link_error_message(LinkStatus.OFFER_EXPIRED).render()[0]]


class TestAFailedAccountLink:
    """The link handlers catch nothing themselves; error_handler answers for them."""

    @pytest.fixture
    def _no_swallowed_crash(self):
        """These tests break a handler on purpose."""
        yield

    async def test_the_chat_is_told_the_session_failed(self, dp, bot, session):
        with patch("apps.bot.handlers.start.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                side_effect=ConnectionError("redis down")
            )
            await dp.feed_update(
                bot, make_message_update("/start sometoken", command=True)
            )

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_session_error_text().render()[0]]

    async def test_a_confirm_tap_is_told_the_session_failed(self, dp, bot, session):
        with patch("apps.bot.handlers.start.start.services") as svc:
            svc.complete_telegram_link = AsyncMock(
                side_effect=ConnectionError("redis down")
            )
            await dp.feed_update(
                bot, make_callback_update(LinkConfirmCB(employee_id=42).pack())
            )

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_session_error_text().render()[0]]
        assert session.calls("editMessageText") == []


class TestAFailedWagonLookup:
    """receive_wagon_number catches nothing itself; error_handler answers for it."""

    @pytest.fixture
    def _no_swallowed_crash(self):
        """These tests break a handler on purpose."""
        yield

    async def test_the_user_can_retry_and_the_log_keeps_what_they_typed_out(
        self, dp, bot, session, state, caplog
    ):
        await save_defect(state, DefectData())
        await state.set_state(DefectSG.wagon_num)

        with patch(
            "apps.bot.handlers.defect.wagon.services.get_wagon_by_number",
            AsyncMock(side_effect=RuntimeError("db down")),
        ):
            await dp.feed_update(bot, make_message_update("Batbayar 99112233"))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_session_error_text().render()[0]]
        assert await state.get_state() == DefectSG.wagon_num.state
        assert await load_defect(state) == DefectData()
        assert "db down" in caplog.text
        assert "Batbayar" not in caplog.text


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
        (sent,) = session.calls("sendMessage")
        assert sent.text == build_defect_cancelled_text().render()[0]
        assert sent.reply_markup == main_menu_keyboard()

    async def test_a_deep_link_does_not_look_up_the_employee(self, dp, bot, session):
        with (
            as_employee(None) as lookup,
            patch("apps.bot.handlers.start.start.services") as svc,
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
