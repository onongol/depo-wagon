"""The defect flow walked end to end through a real Dispatcher.

This is the net the plan asked for. Every step round-trips its form through
storage now, and a handler that mutates the loaded copy without saving it looks
correct in isolation — only a full walk catches it, because the next step reads
the form back.
"""

import uuid
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.bot.callback_data import (
    CB_CANCEL,
    CB_DEFECT_CONTINUE,
    CB_DEFECT_RESTART,
    CB_DESC_SKIP,
    CB_MEAS_BACK,
    CB_MEAS_CLEAR,
    CB_MEAS_DONE,
    CB_PART_NUMBER_SKIP,
    CB_PHOTO_CLEAR,
    CB_PHOTO_SKIP,
    CB_RESP_EMP_ALL,
    CB_RESP_EMP_SKIP,
    CB_STEP_BACK,
    ConfirmCB,
    DefectTypeCB,
    DepartmentCB,
    DimensionCB,
    EditCB,
    NodeCB,
    ResponsibleEmployeeCB,
    SeverityCB,
    VerdictCB,
)
from apps.bot.constants import (
    BTN_OPEN_DEFECTS,
    EDIT_MEASUREMENTS,
    EDIT_RESPONSIBLE,
    FSMKey,
)
from apps.bot.errors import build_session_error_text
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.common.text import build_cancelled_text, build_help_text
from apps.bot.handlers.defect.part_number import PartNumberScene
from apps.bot.handlers.defect.responsible_employee.list import EMPLOYEE_PAGE_SIZE
from apps.bot.handlers.defect.summary import SummaryScene
from apps.bot.handlers.defect.text import (
    build_album_receiving_text,
    build_ask_defect_type_text,
    build_ask_department_text,
    build_ask_description_text,
    build_ask_measurement_text,
    build_ask_node_text,
    build_ask_part_number_text,
    build_ask_photo_text,
    build_ask_responsible_employee_text,
    build_ask_severity_text,
    build_ask_value_text,
    build_ask_verdict_text,
    build_ask_wagon_text,
    build_defect_cancelled_text,
    build_defect_in_progress_text,
    build_edit_defect_type_text,
    build_edit_description_text,
    build_edit_node_text,
    build_edit_photos_text,
    build_edit_severity_text,
    build_edit_verdict_text,
    build_edit_wagon_text,
    build_editing_heading,
    build_fields,
    build_photos_attached_toast,
    build_result_text,
    build_review_heading,
    build_save_failed_text,
    build_save_question_text,
    build_step_heading,
)
from apps.bot.keyboards.common import skip_keyboard, with_step_buttons
from apps.bot.keyboards.confirm import employee_verdict_keyboard
from apps.bot.keyboards.defect import (
    defect_type_keyboard,
    department_keyboard,
    node_keyboard_for_department,
    severity_keyboard,
)
from apps.bot.keyboards.measurement import (
    measurement_keyboard,
    measurement_value_keyboard,
)
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.keyboards.tasks import open_card_keyboard
from apps.bot.middlewares.defect_form import (
    build_form_lost_text,
    build_form_outdated_text,
)
from apps.bot.states import DefectSG
from apps.bot.tests.integration.conftest import (
    CHAT_ID,
    as_employee,
    make_callback_update,
    make_message_update,
    make_photo_update,
)
from apps.bot.user_data import AIResult, DefectData, MeasurementEntry, PhotoEntry
from apps.core.constants import Department
from apps.defects.constants import (
    DefectNode,
    DefectType,
    DefectVerdict,
    MeasurementDimension,
)

WAGON_NUMBER = "60123456"
HUMAN_FACTOR = DefectTypeCB(value=DefectType.HUMAN_FACTOR).pack()


@pytest.fixture
def employee():
    emp = MagicMock()
    emp.id = 7
    emp.full_name = "Bat Erdene"
    emp.role = "inspector"
    emp.get_role_display.return_value = "Inspector"
    return emp


@pytest.fixture
def wagon():
    w = MagicMock()
    w.id = 3
    w.number = WAGON_NUMBER
    return w


@pytest.fixture
def flow(employee, wagon):
    """Everything the walk touches outside the bot itself."""
    saved = MagicMock()
    saved.defect = MagicMock()
    saved.defect.id = uuid.uuid4()
    saved.photo_bytes = []

    with ExitStack() as stack:
        p = stack.enter_context
        lookup = p(as_employee(employee))
        wagon_services = MagicMock()
        wagon_services.get_wagon_by_number = AsyncMock(return_value=wagon)
        p(patch("apps.bot.handlers.defect.wagon.services", wagon_services))
        register = p(
            patch(
                "apps.bot.handlers.defect.confirm.pipeline.persist.register_defect",
                AsyncMock(return_value=saved),
            )
        )
        analysis = p(
            patch(
                "apps.bot.handlers.defect.confirm.handler.run_ai_analysis",
                AsyncMock(return_value=None),
            )
        )
        alert_services = MagicMock()
        alert_services.get_managers_and_engineers = AsyncMock(
            return_value=[MagicMock(id=11)]
        )
        alert_services.queue_messages = AsyncMock()
        p(
            patch(
                "apps.bot.handlers.defect.confirm.pipeline.alert.services",
                alert_services,
            )
        )

        yield MagicMock(
            alert=alert_services,
            analysis=analysis,
            lookup=lookup,
            register=register,
            saved=saved,
            wagon_services=wagon_services,
        )


class TestTheWholeFlow:
    async def test_walks_every_state_and_keeps_the_form(self, dp, bot, state, flow):
        """Each assertion is also a check that the previous step saved its work."""

        async def text(value):
            await dp.feed_update(bot, make_message_update(value))

        async def tap(payload):
            await dp.feed_update(bot, make_callback_update(payload))

        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        assert await state.get_state() == DefectSG.wagon_num.state

        await text(WAGON_NUMBER)
        assert await state.get_state() == DefectSG.department.state

        await tap(DepartmentCB(value=Department.BOGIE).pack())
        assert await state.get_state() == DefectSG.node.state

        await tap(NodeCB(value=DefectNode.WHEEL).pack())
        assert await state.get_state() == DefectSG.part_number.state

        await text("PN-42")
        assert await state.get_state() == DefectSG.defect_type.state

        await tap(DefectTypeCB(value=DefectType.WEAR).pack())
        assert await state.get_state() == DefectSG.photo.state

        await tap(CB_PHOTO_SKIP)
        assert await state.get_state() == DefectSG.measurement_choice.state

        await tap(DimensionCB(value="thickness").pack())
        assert await state.get_state() == DefectSG.measurement_choice.state

        await text("12,5")
        assert await state.get_state() == DefectSG.measurement_choice.state

        await tap(CB_MEAS_DONE)
        assert await state.get_state() == DefectSG.desc.state

        await text("Cracked weld near the flange")
        assert await state.get_state() == DefectSG.severity.state

        await tap(SeverityCB(value="critical").pack())
        assert await state.get_state() == DefectSG.employee_verdict.state

        await tap(VerdictCB(value=DefectVerdict.REPAIR_NOW).pack())
        assert await state.get_state() == DefectSG.confirm.state

        # Everything typed along the way survived every round trip.
        defect = await load_defect(state)
        assert defect.wagon_number == WAGON_NUMBER
        assert defect.wagon_id == 3
        assert defect.department == Department.BOGIE
        assert defect.node == DefectNode.WHEEL
        assert defect.part_number == "PN-42"
        assert defect.defect_type == DefectType.WEAR
        assert defect.severity == "critical"
        assert defect.verdict == DefectVerdict.REPAIR_NOW
        assert defect.description == "Cracked weld near the flange"
        assert len(defect.measurements) == 1
        assert defect.measurements[0].value == 12.5
        assert defect.measurements[0].unit == "mm"

        await tap(ConfirmCB(confirmed=True).pack())
        assert await state.get_state() is None
        assert await load_defect(state) is None
        flow.register.assert_awaited_once()

        # Only start and confirm take the employee
        assert flow.lookup.await_count == 2

    async def test_the_saved_form_reaches_the_persistence_call(
        self, dp, bot, state, flow
    ):
        """What register_defect receives is what the user actually entered."""
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))
        await dp.feed_update(
            bot, make_callback_update(DepartmentCB(value=Department.BOGIE).pack())
        )
        await dp.feed_update(
            bot, make_callback_update(NodeCB(value=DefectNode.WHEEL).pack())
        )
        await dp.feed_update(bot, make_message_update("PN-42"))
        await dp.feed_update(
            bot, make_callback_update(DefectTypeCB(value=DefectType.WEAR).pack())
        )
        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))
        await dp.feed_update(bot, make_callback_update(CB_MEAS_DONE))
        await dp.feed_update(bot, make_message_update("A description"))
        await dp.feed_update(
            bot, make_callback_update(SeverityCB(value="critical").pack())
        )
        await dp.feed_update(
            bot, make_callback_update(VerdictCB(value=DefectVerdict.REPAIR_NOW).pack())
        )
        await dp.feed_update(
            bot, make_callback_update(ConfirmCB(confirmed=True).pack())
        )

        persisted = flow.register.await_args.args[0]
        assert persisted.wagon_number == WAGON_NUMBER
        assert persisted.part_number == "PN-42"
        assert persisted.description == "A description"
        assert persisted.verdict == DefectVerdict.REPAIR_NOW

    async def test_declining_at_the_summary_drops_the_form(self, dp, bot, state, flow):
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))
        await dp.feed_update(
            bot, make_callback_update(DepartmentCB(value=Department.BOGIE).pack())
        )
        await dp.feed_update(
            bot, make_callback_update(NodeCB(value=DefectNode.WHEEL).pack())
        )
        await dp.feed_update(bot, make_message_update("PN-42"))
        await dp.feed_update(
            bot, make_callback_update(DefectTypeCB(value=DefectType.WEAR).pack())
        )
        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))
        await dp.feed_update(bot, make_callback_update(CB_MEAS_DONE))
        await dp.feed_update(bot, make_message_update("A description"))
        await dp.feed_update(
            bot, make_callback_update(SeverityCB(value="critical").pack())
        )
        await dp.feed_update(
            bot, make_callback_update(VerdictCB(value=DefectVerdict.OK).pack())
        )
        assert await state.get_state() == DefectSG.confirm.state

        await dp.feed_update(
            bot, make_callback_update(ConfirmCB(confirmed=False).pack())
        )

        assert await state.get_state() is None
        assert await load_defect(state) is None


class TestConfirmingTwice:
    """A second tap queued behind the first must not save the defect again."""

    async def test_the_form_leaves_confirm_before_it_is_saved(
        self, dp, bot, state, flow
    ):
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(DefectSG.confirm)
        seen = []

        async def register(*args):
            seen.append(await state.get_state())
            return flow.saved

        flow.register.side_effect = register

        await dp.feed_update(
            bot, make_callback_update(ConfirmCB(confirmed=True).pack())
        )

        assert seen == [DefectSG.saving.state]
        assert await state.get_state() is None

    async def test_a_confirm_tap_while_saving_is_absorbed(
        self, dp, bot, session, state, flow
    ):
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(DefectSG.saving)
        session.clear()

        await dp.feed_update(
            bot, make_callback_update(ConfirmCB(confirmed=True).pack())
        )

        flow.register.assert_not_called()
        assert session.method_names() == ["answerCallbackQuery"]
        assert await state.get_state() == DefectSG.saving.state


class TestTheMenuWhileAFormIsOpen:
    """Left in place on the way in; every way out sends it again."""

    async def test_the_way_in_is_the_first_step_alone(self, dp, bot, session, flow):
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))

        (step,) = session.calls("sendMessage")
        assert step.text.startswith(build_step_heading(1, 10).render()[0])
        assert step.text.endswith(build_ask_wagon_text().render()[0])
        assert step.reply_markup == with_step_buttons(None, back=False)

    @pytest.mark.parametrize(
        "step",
        [
            DefectSG.wagon_num,
            DefectSG.part_number,
            DefectSG.photo,
            DefectSG.desc,
            DefectSG.employee_verdict,
        ],
        ids=lambda s: s.state,
    )
    async def test_the_cancel_button_brings_it_back(
        self, dp, bot, session, state, step
    ):
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(step)

        await dp.feed_update(bot, make_callback_update(CB_CANCEL))

        (sent,) = session.calls("sendMessage")
        assert (sent.text, sent.reply_markup) == (
            build_defect_cancelled_text().render()[0],
            main_menu_keyboard(),
        )
        assert await state.get_state() is None
        assert await load_defect(state) is None

    @pytest.mark.parametrize(
        "step",
        [DefectSG.wagon_num, DefectSG.confirm, DefectSG.employee_verdict],
        ids=lambda s: s.state,
    )
    async def test_slash_cancel_brings_it_back_at_any_step(
        self, dp, bot, session, state, step
    ):
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(step)

        await dp.feed_update(bot, make_message_update("/cancel", command=True))

        (sent,) = session.calls("sendMessage")
        assert (sent.text, sent.reply_markup) == (
            build_cancelled_text().render()[0],
            main_menu_keyboard(),
        )
        assert await state.get_state() is None
        assert await load_defect(state) is None

    async def test_a_finished_save_brings_it_back_with_the_result(
        self, dp, bot, session, state, flow
    ):
        """The progress message makes way for the result, which carries the menu."""
        form = DefectData(wagon_id=3, verdict=DefectVerdict.OK)
        await save_defect(state, form)
        await state.set_state(DefectSG.confirm)
        update = make_callback_update(ConfirmCB(confirmed=True).pack())

        await dp.feed_update(bot, update)

        (sent,) = session.calls("sendMessage")
        fields = build_fields(form, SummaryScene.behind(form, {}))
        result = build_result_text(fields, None)
        assert (sent.text, sent.reply_markup) == (
            result.render()[0],
            main_menu_keyboard(),
        )
        deleted = [d.message_id for d in session.calls("deleteMessage")]
        assert deleted == [update.callback_query.message.message_id]
        assert await state.get_state() is None
        assert await load_defect(state) is None

    async def _save_with_recommendation(self, dp, bot, state, flow, recommendation):
        flow.analysis.return_value = AIResult(
            defect_class="Rim wear",
            confidence=0.8,
            verdict=DefectVerdict.REPAIR_SOON,
            rag_recommendation=recommendation,
        )
        await save_defect(state, DefectData(wagon_id=3, verdict=DefectVerdict.OK))
        await state.set_state(DefectSG.confirm)
        await dp.feed_update(
            bot, make_callback_update(ConfirmCB(confirmed=True).pack())
        )

    async def test_the_recommendation_comes_with_the_result(
        self, dp, bot, session, state, flow
    ):
        await self._save_with_recommendation(dp, bot, state, flow, "Replace the pad")

        (sent,) = session.calls("sendMessage")
        assert sent.reply_markup == main_menu_keyboard()
        assert "AI verdict: 🟡 Repair Soon" in sent.text
        assert sent.text.endswith("Replace the pad")

    async def test_one_too_long_for_a_message_follows_it(
        self, dp, bot, session, state, flow
    ):
        await self._save_with_recommendation(dp, bot, state, flow, "x" * 4000)

        card, recommendation = session.calls("sendMessage")
        assert card.reply_markup == main_menu_keyboard()
        assert "AI verdict: 🟡 Repair Soon" in card.text
        assert recommendation.text.endswith("x" * 4000)
        assert recommendation.reply_markup is None

    async def test_a_failed_save_brings_it_back(self, dp, bot, session, state, flow):
        flow.register.side_effect = RuntimeError("db down")
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(DefectSG.confirm)

        await dp.feed_update(
            bot, make_callback_update(ConfirmCB(confirmed=True).pack())
        )

        (sent,) = session.calls("sendMessage")
        assert (sent.text, sent.reply_markup) == (
            build_save_failed_text().render()[0],
            main_menu_keyboard(),
        )
        assert await state.get_state() is None
        assert await load_defect(state) is None


class TestTheDecommissionAlert:
    """Sent once the defect is saved, ahead of the AI."""

    async def _save(self, dp, bot, state, verdict):
        await save_defect(state, DefectData(wagon_id=3, verdict=verdict))
        await state.set_state(DefectSG.confirm)
        await dp.feed_update(
            bot, make_callback_update(ConfirmCB(confirmed=True).pack())
        )

    async def test_a_decommission_verdict_sends_it(
        self, dp, bot, state, flow, employee
    ):
        await self._save(dp, bot, state, DefectVerdict.DECOMMISSION)

        flow.alert.queue_messages.assert_awaited_once()
        ids, text, markup = flow.alert.queue_messages.await_args.args
        assert ids == [11]
        assert employee.full_name in text.render()[0]
        assert markup == open_card_keyboard(flow.saved.defect.id)

    async def test_any_other_verdict_does_not(self, dp, bot, state, flow):
        await self._save(dp, bot, state, DefectVerdict.REPAIR_NOW)

        flow.alert.queue_messages.assert_not_called()

    async def test_a_failed_alert_still_ends_with_the_menu(
        self, dp, bot, session, state, flow
    ):
        flow.alert.queue_messages.side_effect = RuntimeError("broker down")

        await self._save(dp, bot, state, DefectVerdict.DECOMMISSION)

        assert session.calls("sendMessage")[-1].reply_markup == main_menu_keyboard()
        assert await state.get_state() is None


class TestOneScreen:
    """Every step is drawn into one message; typing leaves none."""

    async def test_the_walk_edits_one_message_and_deletes_every_answer(
        self, dp, bot, state, flow, wagon
    ):
        """Wrong answers too: the screen names them. The command that began it stays."""
        session = bot.session
        lookup = flow.wagon_services.get_wagon_by_number
        lookup.side_effect = lambda number: wagon if number == WAGON_NUMBER else None
        typed = []

        async def text(value, **kwargs):
            update = make_message_update(value, **kwargs)
            typed.append(update.message.message_id)
            await dp.feed_update(bot, update)

        async def tap(payload):
            await dp.feed_update(bot, make_callback_update(payload))

        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await text("0000")
        await text(WAGON_NUMBER)
        await tap(DepartmentCB(value=Department.BOGIE).pack())
        await tap(NodeCB(value=DefectNode.WHEEL).pack())
        await text("PN-42")
        await tap(DefectTypeCB(value=DefectType.WEAR).pack())
        await tap(CB_PHOTO_SKIP)
        await tap(DimensionCB(value="thickness").pack())
        await text("twelve")
        await text("12,5")
        await tap(CB_MEAS_DONE)
        await text("Cracked weld near the flange")
        await tap(SeverityCB(value="critical").pack())
        await tap(VerdictCB(value=DefectVerdict.REPAIR_NOW).pack())
        assert await state.get_state() == DefectSG.confirm.state

        assert len(session.calls("sendMessage")) == 1
        _, screen_id = (await state.get_data())[FSMKey.SCREEN]
        edited = {edit.message_id for edit in session.calls("editMessageText")}
        assert edited == {screen_id}
        deleted = [d.message_id for d in session.calls("deleteMessage")]
        assert deleted == typed

    @pytest.mark.parametrize(
        "command", ["/start", "/help", str(BTN_OPEN_DEFECTS)], ids=str
    )
    async def test_a_command_mid_form_stays_and_the_screen_goes_under_it(
        self, dp, bot, session, state, command
    ):
        """Not an answer, so it is not taken off the chat."""
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.part_number)
        await state.update_data({FSMKey.SCREEN: [CHAT_ID, 500]})

        await dp.feed_update(
            bot, make_message_update(command, command=command.startswith("/"))
        )

        (sent,) = session.calls("sendMessage")
        step, _ = await PartNumberScene.draw(await load_defect(state), {})
        assert sent.text == step.render()[0]
        assert [d.message_id for d in session.calls("deleteMessage")] == [500]
        assert await state.get_state() == DefectSG.part_number.state

    async def test_new_defect_mid_form_asks_on_the_screen_and_continue_redraws_it(
        self, dp, bot, session, state, flow
    ):
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))
        session.clear()

        await dp.feed_update(bot, make_message_update("/new_defect", command=True))

        (asked,) = session.calls("sendMessage")
        assert f"🚃 Wagon: {WAGON_NUMBER}" in asked.text
        assert asked.text.endswith(build_defect_in_progress_text().render()[0])
        _, screen = (await state.get_data())[FSMKey.SCREEN]

        await dp.feed_update(bot, make_callback_update(CB_DEFECT_CONTINUE))

        edit = session.calls("editMessageText")[-1]
        assert edit.message_id == screen
        assert edit.text.endswith(build_ask_department_text().render()[0])
        assert await state.get_state() == DefectSG.department.state

    async def test_a_screen_the_user_deleted_is_sent_anew(
        self, dp, bot, session, state, flow
    ):
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        _, first = (await state.get_data())[FSMKey.SCREEN]
        session.refuse("editMessageText", "Bad Request: message to edit not found")

        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))

        assert await state.get_state() == DefectSG.department.state
        sent = session.calls("sendMessage")[-1]
        assert sent.text.endswith(build_ask_department_text().render()[0])
        _, second = (await state.get_data())[FSMKey.SCREEN]
        assert second != first

    async def test_an_over_long_description_stays_and_the_screen_goes_under_it(
        self, dp, bot, session, state
    ):
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.desc)
        await state.update_data({FSMKey.SCREEN: [CHAT_ID, 500]})

        await dp.feed_update(bot, make_message_update("x" * 1001))

        assert await state.get_state() == DefectSG.desc.state
        (sent,) = session.calls("sendMessage")
        assert "1001/1000" in sent.text
        (deleted,) = session.calls("deleteMessage")
        assert deleted.message_id == 500


class TestTheFormEndsCleanly:
    """An exit takes the screen off the chat; the save leaves its result behind."""

    async def _open(self, dp, bot, state):
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        _, screen = (await state.get_data())[FSMKey.SCREEN]
        return screen

    @staticmethod
    def _deleted(session):
        return [d.message_id for d in session.calls("deleteMessage")]

    async def test_cancel_takes_it_down_and_brings_the_menu_back(
        self, dp, bot, session, state, flow
    ):
        screen = await self._open(dp, bot, state)
        session.clear()

        await dp.feed_update(bot, make_callback_update(CB_CANCEL))

        assert self._deleted(session) == [screen]
        (sent,) = session.calls("sendMessage")
        assert sent.reply_markup == main_menu_keyboard()
        assert FSMKey.SCREEN not in await state.get_data()

    async def test_slash_cancel_takes_it_down_too(self, dp, bot, session, state, flow):
        screen = await self._open(dp, bot, state)
        session.clear()

        await dp.feed_update(bot, make_message_update("/cancel", command=True))

        assert self._deleted(session) == [screen]
        assert await state.get_data() == {}

    async def test_a_new_form_takes_down_what_an_abandoned_one_left(
        self, dp, bot, session, state, flow
    ):
        screen = await self._open(dp, bot, state)
        await state.set_state(None)
        session.clear()

        await dp.feed_update(bot, make_message_update("/new_defect", command=True))

        assert self._deleted(session) == [screen]
        assert await state.get_state() == DefectSG.wagon_num.state

    async def test_start_over_keeps_the_screen(self, dp, bot, session, state, flow):
        screen = await self._open(dp, bot, state)
        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))
        session.clear()

        await dp.feed_update(bot, make_callback_update(CB_DEFECT_RESTART))

        assert await state.get_state() == DefectSG.wagon_num.state
        assert (await state.get_data())[FSMKey.SCREEN][1] == screen
        assert session.calls("editMessageText")[-1].message_id == screen
        assert session.calls("deleteMessage") == []

    async def test_the_save_leaves_its_result_behind(
        self, dp, bot, session, state, flow
    ):
        """Only the progress message goes; nothing after it takes the result down."""
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(DefectSG.confirm)
        await state.update_data({FSMKey.SCREEN: [CHAT_ID, 500]})
        update = make_callback_update(ConfirmCB(confirmed=True).pack())

        await dp.feed_update(bot, update)
        await dp.feed_update(bot, make_message_update("/cancel", command=True))

        assert self._deleted(session) == [update.callback_query.message.message_id]
        assert FSMKey.SCREEN not in await state.get_data()


class TestFromTheWagonStepToTheDepartment:
    async def test_a_known_number_shows_the_department_step(
        self, dp, bot, session, state, flow
    ):
        """goto(): the department scene draws its own screen, as a new message."""
        await save_defect(state, DefectData())
        await state.set_state(DefectSG.wagon_num)

        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))

        (sent,) = session.calls("sendMessage")
        assert f"🚃 Wagon: {WAGON_NUMBER}" in sent.text
        assert sent.text.endswith(build_ask_department_text().render()[0])
        assert sent.reply_markup == with_step_buttons(department_keyboard(), back=True)
        assert await state.get_state() == DefectSG.department.state


class TestFromTheDepartmentToTheNode:
    async def test_the_node_scene_draws_its_screen_in_place(
        self, dp, bot, session, state
    ):
        """A tap, so goto() enters by editing the department's message."""
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(DefectSG.department)

        await dp.feed_update(
            bot, make_callback_update(DepartmentCB(value=Department.BOGIE).pack())
        )

        (edit,) = session.calls("editMessageText")
        assert f"🏭 Department: {Department.BOGIE.label}" in edit.text
        assert edit.text.endswith(build_ask_node_text().render()[0])
        assert edit.reply_markup == with_step_buttons(
            node_keyboard_for_department(Department.BOGIE), back=True
        )
        assert await state.get_state() == DefectSG.node.state


class TestEditingTheNode:
    FORM = DefectData(wagon_id=1, department=Department.BOGIE, node="axle")

    async def test_the_scene_offers_the_departments_nodes_in_place(
        self, dp, bot, session, state
    ):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.confirm)

        await dp.feed_update(bot, make_callback_update(EditCB(field="node").pack()))

        (edit,) = session.calls("editMessageText")
        assert edit.text.startswith(build_editing_heading().render()[0])
        assert edit.text.endswith(build_edit_node_text().render()[0])
        assert edit.reply_markup == with_step_buttons(
            node_keyboard_for_department(Department.BOGIE), back=True
        )
        assert await state.get_state() == DefectSG.node.state

    async def test_the_new_node_returns_to_the_summary(self, dp, bot, state):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.confirm)
        await dp.feed_update(bot, make_callback_update(EditCB(field="node").pack()))

        await dp.feed_update(
            bot, make_callback_update(NodeCB(value=DefectNode.WHEEL).pack())
        )

        assert await state.get_state() == DefectSG.confirm.state
        assert FSMKey.EDITING not in await state.get_data()
        assert (await load_defect(state)).node == DefectNode.WHEEL


class TestThePartNumberStep:
    """Skip is an empty part number and a goto(); the next screen shows it as a dash."""

    FORM = DefectData(wagon_id=1, department=Department.BOGIE, node_label="Wheel")

    async def test_the_node_leads_to_it_in_place(self, dp, bot, session, state):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.node)

        await dp.feed_update(
            bot, make_callback_update(NodeCB(value=DefectNode.WHEEL).pack())
        )

        (edit,) = session.calls("editMessageText")
        assert f"🔧 Node: {DefectNode.WHEEL.label}" in edit.text
        assert edit.text.endswith(build_ask_part_number_text().render()[0])
        assert edit.reply_markup == with_step_buttons(
            skip_keyboard(CB_PART_NUMBER_SKIP), back=True
        )
        assert await state.get_state() == DefectSG.part_number.state

    async def test_skip_says_so_and_offers_the_types(self, dp, bot, session, state):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.part_number)

        await dp.feed_update(bot, make_callback_update(CB_PART_NUMBER_SKIP))

        (edit,) = session.calls("editMessageText")
        assert "🔢 Part number: —" in edit.text
        assert edit.text.endswith(build_ask_defect_type_text().render()[0])
        assert edit.reply_markup == with_step_buttons(defect_type_keyboard(), back=True)
        assert await state.get_state() == DefectSG.defect_type.state
        assert (await load_defect(state)).part_number == ""

    async def test_a_typed_one_is_confirmed_as_typed(self, dp, bot, session, state):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.part_number)

        await dp.feed_update(bot, make_message_update("<PN-42>"))

        (sent,) = session.calls("sendMessage")
        assert "🔢 Part number: <PN-42>" in sent.text
        assert sent.text.endswith(build_ask_defect_type_text().render()[0])
        assert sent.reply_markup == with_step_buttons(defect_type_keyboard(), back=True)
        assert (await load_defect(state)).part_number == "<PN-42>"

    async def test_skip_from_an_edit_clears_it_and_goes_back(self, dp, bot, state):
        await save_defect(state, DefectData(wagon_id=1, part_number="PN-1"))
        await state.set_state(DefectSG.confirm)
        tap = EditCB(field="part_number").pack()
        await dp.feed_update(bot, make_callback_update(tap))

        await dp.feed_update(bot, make_callback_update(CB_PART_NUMBER_SKIP))

        assert await state.get_state() == DefectSG.confirm.state
        assert FSMKey.EDITING not in await state.get_data()
        assert (await load_defect(state)).part_number == ""


class TestEditingTheDefectType:
    async def test_the_scene_asks_and_the_answer_goes_back(
        self, dp, bot, session, state
    ):
        await save_defect(state, DefectData(wagon_id=1, defect_type=DefectType.WEAR))
        await state.set_state(DefectSG.confirm)

        await dp.feed_update(
            bot, make_callback_update(EditCB(field="defect_type").pack())
        )
        (edit,) = session.calls("editMessageText")
        assert edit.text.endswith(build_edit_defect_type_text().render()[0])
        assert await state.get_state() == DefectSG.defect_type.state

        tap = DefectTypeCB(value=DefectType.CRACK).pack()
        await dp.feed_update(bot, make_callback_update(tap))

        assert await state.get_state() == DefectSG.confirm.state
        assert (await load_defect(state)).defect_type == DefectType.CRACK


class TestFromTheTypeToThePhotos:
    async def test_the_type_leads_to_the_photo_step_in_place(
        self, dp, bot, session, state
    ):
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.defect_type)

        tap = DefectTypeCB(value=DefectType.CRACK).pack()
        await dp.feed_update(bot, make_callback_update(tap))

        (edit,) = session.calls("editMessageText")
        assert f"⚠️ Defect type: {DefectType.CRACK.label}" in edit.text
        assert edit.text.endswith(build_ask_photo_text().render()[0])
        assert edit.reply_markup == with_step_buttons(
            skip_keyboard(CB_PHOTO_SKIP), back=True
        )
        assert await state.get_state() == DefectSG.photo.state


class TestTheSeverityStep:
    """After the description; the verdict comes next."""

    async def test_a_description_leads_to_it(self, dp, bot, session, state):
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.desc)

        await dp.feed_update(bot, make_message_update("Cracked weld"))

        (sent,) = session.calls("sendMessage")
        assert "📝 Description: \nCracked weld" in sent.text
        assert sent.text.endswith(build_ask_severity_text().render()[0])
        assert sent.reply_markup == with_step_buttons(severity_keyboard(), back=True)
        assert await state.get_state() == DefectSG.severity.state

    async def test_a_skipped_description_leads_to_it_in_place(
        self, dp, bot, session, state
    ):
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.desc)

        await dp.feed_update(bot, make_callback_update(CB_DESC_SKIP))

        (edit,) = session.calls("editMessageText")
        assert "📝 Description: —" in edit.text
        assert edit.text.endswith(build_ask_severity_text().render()[0])
        assert await state.get_state() == DefectSG.severity.state

    async def test_it_leads_to_the_verdict_in_place(self, dp, bot, session, state):
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.severity)

        await dp.feed_update(bot, make_callback_update(SeverityCB(value="high").pack()))

        (edit,) = session.calls("editMessageText")
        assert "🌡️ Severity: 🟠 High" in edit.text
        assert edit.text.endswith(build_ask_verdict_text().render()[0])
        assert edit.reply_markup == with_step_buttons(
            employee_verdict_keyboard(), back=True
        )
        assert await state.get_state() == DefectSG.employee_verdict.state

    async def test_an_edit_asks_again_and_goes_back(self, dp, bot, session, state):
        await save_defect(state, DefectData(wagon_id=1, severity="low"))
        await state.set_state(DefectSG.confirm)

        await dp.feed_update(bot, make_callback_update(EditCB(field="severity").pack()))
        (edit,) = session.calls("editMessageText")
        assert edit.text.endswith(build_edit_severity_text().render()[0])
        assert edit.reply_markup == with_step_buttons(severity_keyboard(), back=True)

        await dp.feed_update(bot, make_callback_update(SeverityCB(value="high").pack()))

        assert await state.get_state() == DefectSG.confirm.state
        assert (await load_defect(state)).severity == "high"


class TestTheVerdictStep:
    """Last in the form, so the AI's verdict is not seen before it."""

    async def test_it_leads_to_the_summary_in_place(self, dp, bot, session, state):
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.employee_verdict)

        tap = VerdictCB(value=DefectVerdict.REPAIR_SOON).pack()
        await dp.feed_update(bot, make_callback_update(tap))

        (edit,) = session.calls("editMessageText")
        assert edit.text.startswith(build_review_heading().render()[0])
        assert "👨‍🔧 Verdict: 🟡 Repair Soon" in edit.text
        assert edit.text.endswith(build_save_question_text().render()[0])
        assert await state.get_state() == DefectSG.confirm.state

    async def test_an_edit_asks_again_and_goes_back(self, dp, bot, session, state):
        form = DefectData(wagon_id=1, verdict=DefectVerdict.OK, verdict_label="✅ OK")
        await save_defect(state, form)
        await state.set_state(DefectSG.confirm)

        await dp.feed_update(bot, make_callback_update(EditCB(field="verdict").pack()))
        (edit,) = session.calls("editMessageText")
        assert edit.text.endswith(build_edit_verdict_text().render()[0])

        tap = VerdictCB(value=DefectVerdict.DECOMMISSION).pack()
        await dp.feed_update(bot, make_callback_update(tap))

        assert await state.get_state() == DefectSG.confirm.state
        assert (await load_defect(state)).verdict == DefectVerdict.DECOMMISSION

    async def test_back_returns_to_the_severity(self, dp, bot, session, state):
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.employee_verdict)

        await dp.feed_update(bot, make_callback_update(CB_STEP_BACK))

        assert await state.get_state() == DefectSG.severity.state


class TestTheMeasurementCard:
    """One state throughout: the picked dimension waits in the form for its number."""

    THICKNESS = MeasurementEntry(
        dimension="thickness", dimension_label="Thickness", unit="mm"
    )

    async def _at_the_card(self, state, **form):
        await save_defect(state, DefectData(wagon_id=1, **form))
        await state.set_state(DefectSG.measurement_choice)

    async def test_the_photos_lead_to_it_in_place(self, dp, bot, session, state):
        await save_defect(state, DefectData(wagon_id=1, defect_type=DefectType.WEAR))
        await state.set_state(DefectSG.photo)

        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))

        (edit,) = session.calls("editMessageText")
        assert edit.text.endswith(
            build_ask_measurement_text(any_saved=False).render()[0]
        )
        assert edit.reply_markup == with_step_buttons(
            measurement_keyboard(any_saved=False), back=True
        )
        assert await state.get_state() == DefectSG.measurement_choice.state

    async def test_a_dimension_asks_for_its_number_in_place(
        self, dp, bot, session, state
    ):
        await self._at_the_card(state)

        tap = DimensionCB(value=MeasurementDimension.THICKNESS).pack()
        await dp.feed_update(bot, make_callback_update(tap))

        (edit,) = session.calls("editMessageText")
        expected = build_ask_value_text("Thickness", "mm")
        assert edit.text.endswith(expected.render()[0])
        assert edit.reply_markup == with_step_buttons(
            measurement_value_keyboard(), back=False
        )
        assert (await load_defect(state)).current_measurement == self.THICKNESS

    async def test_the_number_joins_the_fields_over_the_card(
        self, dp, bot, session, state
    ):
        await self._at_the_card(state, current_measurement=self.THICKNESS)

        await dp.feed_update(bot, make_message_update("12,5"))

        (sent,) = session.calls("sendMessage")
        assert "📐 Measurements: 1\n🔹 Thickness: 12.5 mm" in sent.text
        assert sent.text.endswith(
            build_ask_measurement_text(any_saved=True).render()[0]
        )
        assert sent.reply_markup == with_step_buttons(
            measurement_keyboard(any_saved=True), back=True
        )
        assert await state.get_state() == DefectSG.measurement_choice.state

    async def test_back_returns_to_the_card_in_place(self, dp, bot, session, state):
        await self._at_the_card(state, current_measurement=self.THICKNESS)

        await dp.feed_update(bot, make_callback_update(CB_MEAS_BACK))

        (edit,) = session.calls("editMessageText")
        assert edit.text.endswith(
            build_ask_measurement_text(any_saved=False).render()[0]
        )
        assert (await load_defect(state)).current_measurement is None

    async def test_a_menu_button_keeps_the_picked_dimension(
        self, dp, bot, session, state
    ):
        await self._at_the_card(state, current_measurement=self.THICKNESS)

        await dp.feed_update(bot, make_message_update("/help", command=True))

        (sent,) = session.calls("sendMessage")
        expected = build_ask_value_text("Thickness", "mm")
        assert sent.text.endswith(expected.render()[0])
        assert sent.reply_markup == with_step_buttons(
            measurement_value_keyboard(), back=False
        )


class TestTheDescriptionStep:
    async def test_done_on_the_card_leads_to_it_in_place(self, dp, bot, session, state):
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.measurement_choice)

        await dp.feed_update(bot, make_callback_update(CB_MEAS_DONE))

        (edit,) = session.calls("editMessageText")
        assert edit.text.endswith(build_ask_description_text().render()[0])
        assert edit.reply_markup == with_step_buttons(
            skip_keyboard(CB_DESC_SKIP), back=True
        )
        assert await state.get_state() == DefectSG.desc.state

    async def test_an_edit_asks_again_and_goes_back(self, dp, bot, session, state):
        await save_defect(state, DefectData(wagon_id=1, description="Old"))
        await state.set_state(DefectSG.confirm)

        tap = EditCB(field="description").pack()
        await dp.feed_update(bot, make_callback_update(tap))
        (edit,) = session.calls("editMessageText")
        assert edit.text.endswith(build_edit_description_text().render()[0])
        assert await state.get_state() == DefectSG.desc.state

        await dp.feed_update(bot, make_message_update("Cracked weld"))

        assert await state.get_state() == DefectSG.confirm.state
        assert (await load_defect(state)).description == "Cracked weld"
        assert FSMKey.EDITING not in await state.get_data()


class TestEditingThePhotos:
    """Edit reopens the photos there: more can be sent, or all cleared."""

    PHOTO = PhotoEntry(file_id="AgAC", message_id=10)

    async def _open(self, dp, bot, state):
        form = DefectData(wagon_id=1, defect_type=DefectType.WEAR, photos=[self.PHOTO])
        await save_defect(state, form)
        await state.set_state(DefectSG.confirm)
        await dp.feed_update(bot, make_callback_update(EditCB(field="photos").pack()))

    async def test_it_counts_them_in_place(self, dp, bot, session, state):
        await self._open(dp, bot, state)

        (edit,) = session.calls("editMessageText")
        assert "📸 Photos: 1" in edit.text
        assert edit.text.endswith(build_edit_photos_text(any_attached=True).render()[0])
        assert await state.get_state() == DefectSG.photo.state

    async def test_a_new_photo_joins_them_and_done_goes_back(self, dp, bot, state):
        await self._open(dp, bot, state)

        await dp.feed_update(bot, make_photo_update("AgAD", message_id=20))
        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))

        assert await state.get_state() == DefectSG.confirm.state
        photos = (await load_defect(state)).photos
        assert [p.file_id for p in photos] == ["AgAC", "AgAD"]
        assert FSMKey.EDITING not in await state.get_data()

    async def test_clear_then_done_goes_back_with_none(self, dp, bot, state):
        await self._open(dp, bot, state)

        await dp.feed_update(bot, make_callback_update(CB_PHOTO_CLEAR))
        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))

        assert await state.get_state() == DefectSG.confirm.state
        assert (await load_defect(state)).photos == []


class TestEditingTheMeasurements:
    GAP = MeasurementEntry(dimension="gap", dimension_label="Gap", unit="mm")

    async def test_clear_then_a_new_one_then_done_goes_back(
        self, dp, bot, session, state
    ):
        old = self.GAP.model_copy(update={"value": 9.0})
        form = DefectData(wagon_id=1, defect_type=DefectType.WEAR, measurements=[old])
        await save_defect(state, form)
        await state.set_state(DefectSG.confirm)

        tap = EditCB(field=EDIT_MEASUREMENTS).pack()
        await dp.feed_update(bot, make_callback_update(tap))
        (edit,) = session.calls("editMessageText")
        assert "🔹 Gap: 9.0 mm" in edit.text
        card = measurement_keyboard(any_saved=True, clearable=True)
        assert edit.reply_markup == with_step_buttons(card, back=True)

        await dp.feed_update(bot, make_callback_update(CB_MEAS_CLEAR))
        gap = DimensionCB(value=MeasurementDimension.GAP).pack()
        await dp.feed_update(bot, make_callback_update(gap))
        await dp.feed_update(bot, make_message_update("3"))
        await dp.feed_update(bot, make_callback_update(CB_MEAS_DONE))

        assert await state.get_state() == DefectSG.confirm.state
        saved = (await load_defect(state)).measurements
        assert saved == [self.GAP.model_copy(update={"value": 3.0})]
        assert FSMKey.EDITING not in await state.get_data()


class TestGoingBack:
    FORM = DefectData(
        wagon_id=1,
        wagon_number=WAGON_NUMBER,
        department=Department.BOGIE,
        node=DefectNode.WHEEL,
        defect_type=DefectType.WEAR,
        description="Cracked weld",
    )

    async def test_back_walks_the_steps_in_reverse_and_keeps_the_form(
        self, dp, bot, state
    ):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.severity)

        visited = []
        for _ in range(9):
            await dp.feed_update(bot, make_callback_update(CB_STEP_BACK))
            visited.append(await state.get_state())

        assert visited == [
            DefectSG.desc.state,
            DefectSG.measurement_choice.state,
            DefectSG.photo.state,
            DefectSG.defect_type.state,
            DefectSG.part_number.state,
            DefectSG.node.state,
            DefectSG.department.state,
            DefectSG.wagon_num.state,
            DefectSG.wagon_num.state,
        ]
        assert await load_defect(state) == self.FORM

    async def test_the_step_is_redrawn_in_place_with_back(
        self, dp, bot, session, state
    ):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.node)

        await dp.feed_update(bot, make_callback_update(CB_STEP_BACK))

        (edit,) = session.calls("editMessageText")
        assert f"🚃 Wagon: {WAGON_NUMBER}" in edit.text
        assert edit.text.endswith(build_ask_department_text().render()[0])
        assert edit.reply_markup == with_step_buttons(department_keyboard(), back=True)

    async def test_back_from_an_edit_returns_to_the_summary_unchanged(
        self, dp, bot, state
    ):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.confirm)
        await dp.feed_update(bot, make_callback_update(EditCB(field="node").pack()))

        await dp.feed_update(bot, make_callback_update(CB_STEP_BACK))

        assert await state.get_state() == DefectSG.confirm.state
        assert FSMKey.EDITING not in await state.get_data()
        assert await load_defect(state) == self.FORM


class TestEditingTheWagon:
    """Edit ▸ Wagon enters the wagon scene from the summary, a plain step."""

    FORM = DefectData(wagon_id=1, wagon_number="11111111", node="wheel")

    async def test_the_scene_asks_for_the_new_number_in_place(
        self, dp, bot, session, state
    ):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.confirm)

        await dp.feed_update(bot, make_callback_update(EditCB(field="wagon").pack()))

        edits = [e.text for e in session.calls("editMessageText")]
        (edit,) = edits
        assert edit.endswith(build_edit_wagon_text().render()[0])
        assert await state.get_state() == DefectSG.wagon_num.state
        assert (await state.get_data())[FSMKey.EDITING] is True

    async def test_the_new_number_returns_to_the_summary(
        self, dp, bot, session, state, flow
    ):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.confirm)
        await dp.feed_update(bot, make_callback_update(EditCB(field="wagon").pack()))

        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))

        assert await state.get_state() == DefectSG.confirm.state
        assert FSMKey.EDITING not in await state.get_data()
        defect = await load_defect(state)
        assert (defect.wagon_number, defect.node) == (WAGON_NUMBER, "wheel")


class TestAFormLeftOverFromAnEarlierBuild:
    """A deploy lands mid-flow and the stored form no longer matches the code.

    No step checks the None load_defect returns for it; they all assign onto the
    form. Without the middleware this walk ends in an AttributeError:
    error_handler's generic session error, and the stale form left in place to
    trip the next tap too — the assertions below pin the reset.
    """

    async def _mid_flow_with_a_foreign_schema(self, dp, bot, state):
        from apps.bot.constants import FSMKey
        from apps.bot.user_data import STATE_SCHEMA_VERSION

        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))
        await dp.feed_update(
            bot, make_callback_update(DepartmentCB(value=Department.BOGIE).pack())
        )
        assert await state.get_state() == DefectSG.node.state

        stored = (await state.get_data())[FSMKey.DEFECT]
        stored["_schema"] = STATE_SCHEMA_VERSION + 1
        await state.update_data({FSMKey.DEFECT: stored})

    async def test_the_next_tap_resets_the_flow_instead_of_raising(
        self, dp, bot, state, session, flow
    ):
        await self._mid_flow_with_a_foreign_schema(dp, bot, state)
        session.clear()

        await dp.feed_update(
            bot, make_callback_update(NodeCB(value=DefectNode.WHEEL).pack())
        )

        assert await state.get_state() is None
        assert await load_defect(state) is None
        sent = session.calls("sendMessage")
        assert [m.text for m in sent] == [build_form_outdated_text().render()[0]]
        assert sent[0].reply_markup == main_menu_keyboard()

    async def test_the_user_can_start_a_fresh_form_straight_after(
        self, dp, bot, state, session, flow
    ):
        await self._mid_flow_with_a_foreign_schema(dp, bot, state)
        await dp.feed_update(
            bot, make_callback_update(NodeCB(value=DefectNode.WHEEL).pack())
        )
        session.clear()

        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))

        assert await state.get_state() == DefectSG.department.state
        assert (await load_defect(state)).wagon_number == WAGON_NUMBER

    async def test_a_form_left_behind_does_not_hijack_another_feature(
        self, dp, bot, state, session, flow
    ):
        """A failed save leaves the form but not the state; /help still gets help."""
        from apps.bot.constants import FSMKey

        await self._mid_flow_with_a_foreign_schema(dp, bot, state)
        await state.set_state(None)
        session.clear()

        await dp.feed_update(bot, make_message_update("/help", command=True))

        assert [m.text for m in session.calls("sendMessage")] == [
            build_help_text().render()[0]
        ]
        assert FSMKey.DEFECT not in await state.get_data()


class TestAStepWithoutItsForm:
    """The state outlived the form: its key expired first, or an exit half-failed.

    Before the middleware covered this, most steps raised AttributeError and
    left the state in place to raise again on the next update.
    """

    @pytest.mark.parametrize("step", DefectSG.__states__, ids=lambda s: s.state)
    async def test_a_message_ends_the_flow_instead_of_raising(
        self, dp, bot, session, state, step
    ):
        await state.set_state(step)

        await dp.feed_update(bot, make_message_update("12.5"))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_form_lost_text().render()[0]]
        assert await state.get_state() is None

    async def test_a_tap_ends_it_too(self, dp, bot, session, state):
        await state.set_state(DefectSG.measurement_choice)
        tap = DimensionCB(value=MeasurementDimension.DEPTH).pack()

        await dp.feed_update(bot, make_callback_update(tap))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [build_form_lost_text().render()[0]]
        assert await state.get_state() is None


async def _to_the_type_step(dp, bot):
    await dp.feed_update(bot, make_message_update("/new_defect", command=True))
    await dp.feed_update(bot, make_message_update(WAGON_NUMBER))
    await dp.feed_update(
        bot, make_callback_update(DepartmentCB(value=Department.BOGIE).pack())
    )
    await dp.feed_update(
        bot, make_callback_update(NodeCB(value=DefectNode.WHEEL).pack())
    )
    await dp.feed_update(bot, make_message_update("PN-42"))


class TestHumanFactorBranch:
    ROSTER = tuple(MagicMock(id=i, first_name=f"U{i}", last_name="L") for i in range(3))

    @pytest.fixture
    def roster(self):
        with ExitStack() as stack:
            p = stack.enter_context
            p(
                patch(
                    "apps.bot.services.count_department_employees",
                    AsyncMock(return_value=len(self.ROSTER)),
                )
            )
            search = p(
                patch(
                    "apps.bot.services.get_department_employees",
                    AsyncMock(return_value=list(self.ROSTER)),
                )
            )
            p(
                patch(
                    "apps.bot.services.get_department_employee",
                    AsyncMock(return_value=self.ROSTER[1]),
                )
            )
            yield search

    async def _up_to_the_type(self, dp, bot):
        await _to_the_type_step(dp, bot)
        await dp.feed_update(bot, make_callback_update(HUMAN_FACTOR))

    @pytest.mark.usefixtures("flow", "roster")
    async def test_the_employee_comes_straight_after_the_type(
        self, dp, bot, session, state
    ):
        await self._up_to_the_type(dp, bot)

        assert await state.get_state() == DefectSG.responsible_employee.state
        edit = session.calls("editMessageText")[-1]
        assert [row[0].text for row in edit.reply_markup.inline_keyboard[:3]] == [
            "U0 L",
            "U1 L",
            "U2 L",
        ]

    @pytest.mark.usefixtures("flow", "roster")
    async def test_the_pick_is_named_on_the_photo_screen(self, dp, bot, session, state):
        await self._up_to_the_type(dp, bot)

        await dp.feed_update(
            bot, make_callback_update(ResponsibleEmployeeCB(employee_id=1).pack())
        )

        assert await state.get_state() == DefectSG.photo.state
        assert (await load_defect(state)).responsible_employee_label == "U1 L"
        edit = session.calls("editMessageText")[-1]
        assert "👤 Responsible: U1 L" in edit.text
        assert edit.text.endswith(build_ask_photo_text().render()[0])
        assert edit.reply_markup == with_step_buttons(
            skip_keyboard(CB_PHOTO_SKIP), back=True
        )

    @pytest.mark.usefixtures("flow", "roster")
    async def test_skipped_it_goes_on_through_the_photos_to_the_description(
        self, dp, bot, state
    ):
        """No measurements for a human factor."""
        await self._up_to_the_type(dp, bot)

        await dp.feed_update(bot, make_callback_update(CB_RESP_EMP_SKIP))
        assert await state.get_state() == DefectSG.photo.state

        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))

        assert await state.get_state() == DefectSG.desc.state
        assert (await load_defect(state)).responsible_employee_id is None

    @pytest.mark.usefixtures("flow")
    async def test_a_typed_name_narrows_the_list_in_place(
        self, dp, bot, session, state, roster
    ):
        await self._up_to_the_type(dp, bot)
        session.clear()
        typed = make_message_update("U1")

        await dp.feed_update(bot, typed)

        roster.assert_awaited_with(
            Department.BOGIE, "U1", limit=EMPLOYEE_PAGE_SIZE, offset=0
        )
        (deleted,) = session.calls("deleteMessage")
        assert deleted.message_id == typed.message.message_id
        assert session.calls("sendMessage") == []
        (edit,) = session.calls("editMessageText")
        assert "U1" in edit.text
        assert await state.get_state() == DefectSG.responsible_employee.state

    @pytest.mark.usefixtures("flow")
    async def test_all_employees_undoes_a_search_that_found_nobody(
        self, dp, bot, session, state, roster
    ):
        await self._up_to_the_type(dp, bot)
        await dp.feed_update(bot, make_message_update("Bt"))
        session.clear()

        await dp.feed_update(bot, make_callback_update(CB_RESP_EMP_ALL))

        roster.assert_awaited_with(
            Department.BOGIE, "", limit=EMPLOYEE_PAGE_SIZE, offset=0
        )
        (edit,) = session.calls("editMessageText")
        expected = build_ask_responsible_employee_text(1, 1, len(self.ROSTER))
        assert edit.text.endswith(expected.render()[0])
        assert await state.get_state() == DefectSG.responsible_employee.state

    @pytest.mark.usefixtures("flow", "roster")
    async def test_edit_type_to_a_human_factor_asks_then_returns_to_the_summary(
        self, dp, bot, state
    ):
        await save_defect(
            state,
            DefectData(
                wagon_id=3,
                wagon_number=WAGON_NUMBER,
                department=Department.BOGIE.value,
                defect_type=DefectType.WEAR,
                defect_type_label="Wear",
            ),
        )
        await state.set_state(DefectSG.confirm)

        await dp.feed_update(
            bot, make_callback_update(EditCB(field="defect_type").pack())
        )
        await dp.feed_update(bot, make_callback_update(HUMAN_FACTOR))
        assert await state.get_state() == DefectSG.responsible_employee.state

        await dp.feed_update(
            bot, make_callback_update(ResponsibleEmployeeCB(employee_id=1).pack())
        )

        assert await state.get_state() == DefectSG.confirm.state
        assert FSMKey.EDITING not in await state.get_data()
        assert (await load_defect(state)).responsible_employee_label == "U1 L"

    @pytest.mark.usefixtures("flow", "roster")
    async def test_edit_type_to_a_human_factor_again_keeps_the_employee(
        self, dp, bot, session, state
    ):
        await save_defect(
            state,
            DefectData(
                wagon_id=3,
                wagon_number=WAGON_NUMBER,
                department=Department.BOGIE.value,
                defect_type=DefectType.HUMAN_FACTOR,
                defect_type_label="Human Factor",
                responsible_employee_id=1,
                responsible_employee_label="U1 L",
            ),
        )
        await state.set_state(DefectSG.confirm)

        await dp.feed_update(
            bot, make_callback_update(EditCB(field="defect_type").pack())
        )
        await dp.feed_update(bot, make_callback_update(HUMAN_FACTOR))

        assert await state.get_state() == DefectSG.confirm.state
        assert FSMKey.EDITING not in await state.get_data()
        assert (await load_defect(state)).responsible_employee_id == 1
        assert "U1 L" in session.calls("editMessageText")[-1].text

    @pytest.mark.usefixtures("flow", "roster")
    async def test_edit_responsible_swaps_the_employee(self, dp, bot, session, state):
        await save_defect(
            state,
            DefectData(
                wagon_id=3,
                wagon_number=WAGON_NUMBER,
                department=Department.BOGIE.value,
                defect_type=DefectType.HUMAN_FACTOR,
                defect_type_label="Human Factor",
                responsible_employee_id=2,
                responsible_employee_label="U2 L",
            ),
        )
        await state.set_state(DefectSG.confirm)

        edit = EditCB(field=EDIT_RESPONSIBLE).pack()
        await dp.feed_update(bot, make_callback_update(edit))
        assert await state.get_state() == DefectSG.responsible_employee.state

        await dp.feed_update(
            bot, make_callback_update(ResponsibleEmployeeCB(employee_id=1).pack())
        )

        assert await state.get_state() == DefectSG.confirm.state
        assert (await load_defect(state)).responsible_employee_id == 1
        summary = session.calls("editMessageText")[-1]
        assert "U1 L" in summary.text
        buttons = [
            b.callback_data for row in summary.reply_markup.inline_keyboard for b in row
        ]
        assert edit in buttons


class TestAFailedEmployeeLookup:
    @pytest.fixture(autouse=True)
    def _no_swallowed_crash(self):
        """These tests break the lookup on purpose."""
        yield

    @pytest.mark.usefixtures("flow")
    async def test_keeps_the_type_step_for_its_buttons_to_retry(
        self, dp, bot, session, state
    ):
        """aiogram moves the state before the list is drawn; the type step moves it back."""
        await _to_the_type_step(dp, bot)

        with patch(
            "apps.bot.services.count_department_employees",
            AsyncMock(side_effect=RuntimeError("db down")),
        ):
            await dp.feed_update(bot, make_callback_update(HUMAN_FACTOR))

        assert await state.get_state() == DefectSG.defect_type.state
        told = session.calls("sendMessage")[-1]
        assert told.text == build_session_error_text().render()[0]

        with (
            patch(
                "apps.bot.services.count_department_employees",
                AsyncMock(return_value=0),
            ),
            patch(
                "apps.bot.services.get_department_employees", AsyncMock(return_value=[])
            ),
        ):
            await dp.feed_update(bot, make_callback_update(HUMAN_FACTOR))

        assert await state.get_state() == DefectSG.responsible_employee.state


class TestAlbum:
    async def test_three_photos_are_recorded_and_answered_once_then_counted(
        self, dp, bot, session, state, flow
    ):
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))
        await dp.feed_update(
            bot, make_callback_update(DepartmentCB(value=Department.BOGIE).pack())
        )
        await dp.feed_update(
            bot, make_callback_update(NodeCB(value=DefectNode.WHEEL).pack())
        )
        await dp.feed_update(bot, make_message_update("PN-42"))
        await dp.feed_update(
            bot, make_callback_update(DefectTypeCB(value=DefectType.WEAR).pack())
        )
        assert await state.get_state() == DefectSG.photo.state

        _, before = (await state.get_data())[FSMKey.SCREEN]
        session.clear()
        # Concurrent handling can reach the album in any order.
        for i in (2, 0, 1):
            await dp.feed_update(
                bot,
                make_photo_update(
                    f"file{i}", media_group_id="mg-1", message_id=10_000 + i
                ),
            )

        defect = await load_defect(state)
        assert [p.file_id for p in defect.photos] == ["file0", "file1", "file2"]
        (screen,) = session.calls("sendMessage")
        assert build_album_receiving_text().render()[0] in screen.text
        assert "📸 Photos: 1" in screen.text
        assert [d.message_id for d in session.calls("deleteMessage")] == [before]
        _, after = (await state.get_data())[FSMKey.SCREEN]

        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))

        toast = session.calls("answerCallbackQuery")[-1]
        assert toast.text == build_photos_attached_toast(3)
        assert await state.get_state() == DefectSG.measurement_choice.state
        assert session.calls("editMessageText")[-1].message_id == after

    async def test_a_lone_photo_gets_the_screen_under_it_at_once(
        self, dp, bot, session, state, flow
    ):
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await state.set_state(DefectSG.photo)
        session.clear()

        await dp.feed_update(bot, make_photo_update("solo"))

        assert len(session.calls("sendMessage")) == 1
