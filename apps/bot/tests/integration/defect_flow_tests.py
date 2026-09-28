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
from aiogram.types import ReplyKeyboardRemove

from apps.bot.callback_data import (
    CB_CANCEL,
    CB_MEAS_ADD,
    CB_MEAS_DONE,
    CB_PART_NUMBER_SKIP,
    CB_PHOTO_SKIP,
    CB_RESP_EMP_SKIP,
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
from apps.bot.constants import SEVERITY_LABELS, UD_EDITING
from apps.bot.errors import build_session_error_text
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.common.text import build_help_text
from apps.bot.handlers.defect.responsible_employee.list import EMPLOYEE_PAGE_SIZE
from apps.bot.handlers.defect.text import (
    build_album_receiving_text,
    build_defect_type_confirmed_text,
    build_department_confirmed_text,
    build_edit_defect_type_text,
    build_edit_node_text,
    build_edit_wagon_text,
    build_node_confirmed_text,
    build_part_number_confirmed_text,
    build_part_number_skipped_text,
    build_photos_attached_toast,
    build_responsible_employee_confirmed_text,
    build_severity_confirmed_text,
    build_wagon_confirmed_text,
)
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import (
    defect_type_keyboard,
    department_keyboard,
    node_keyboard_for_department,
    severity_keyboard,
)
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.tests.integration.conftest import (
    as_employee,
    make_callback_update,
    make_message_update,
    make_photo_update,
)
from apps.bot.user_data import DefectData
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
                "apps.bot.handlers.defect.confirm.handler.register_defect",
                AsyncMock(return_value=saved),
            )
        )
        p(
            patch(
                "apps.bot.handlers.defect.confirm.handler.run_ai_analysis",
                AsyncMock(return_value=None),
            )
        )
        verdict_services = MagicMock()
        verdict_services.save_employee_verdict = AsyncMock()
        p(patch("apps.bot.handlers.defect.verdict.services", verdict_services))

        yield MagicMock(
            lookup=lookup,
            register=register,
            saved=saved,
            verdict_services=verdict_services,
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
        assert await state.get_state() == DefectSG.severity.state

        await tap(SeverityCB(value="critical").pack())
        assert await state.get_state() == DefectSG.photo.state

        await tap(CB_PHOTO_SKIP)
        assert await state.get_state() == DefectSG.measurement_choice.state

        await tap(CB_MEAS_ADD)
        assert await state.get_state() == DefectSG.measurement_dimension.state

        await tap(DimensionCB(value="thickness").pack())
        assert await state.get_state() == DefectSG.measurement_value.state

        await text("12,5")
        assert await state.get_state() == DefectSG.measurement_norm.state

        await text("14")
        assert await state.get_state() == DefectSG.measurement_unit.state

        await text("mm")
        assert await state.get_state() == DefectSG.measurement_choice.state

        await tap(CB_MEAS_DONE)
        assert await state.get_state() == DefectSG.desc.state

        await text("Cracked weld near the flange")
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
        assert defect.description == "Cracked weld near the flange"
        assert len(defect.measurements) == 1
        assert defect.measurements[0].value == 12.5
        assert defect.measurements[0].norm_value == 14.0
        assert defect.measurements[0].unit == "mm"

        await tap(ConfirmCB(confirmed=True).pack())
        assert await state.get_state() == DefectSG.employee_verdict.state
        flow.register.assert_awaited_once()

        await tap(VerdictCB(value=DefectVerdict.REPAIR_NOW).pack())
        assert await state.get_state() is None
        flow.verdict_services.save_employee_verdict.assert_awaited_once()

        # Only start, confirm and verdict take the employee
        assert flow.lookup.await_count == 3

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
        await dp.feed_update(
            bot, make_callback_update(SeverityCB(value="critical").pack())
        )
        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))
        await dp.feed_update(bot, make_callback_update(CB_MEAS_DONE))
        await dp.feed_update(bot, make_message_update("A description"))
        await dp.feed_update(
            bot, make_callback_update(ConfirmCB(confirmed=True).pack())
        )

        persisted = flow.register.await_args.args[0]
        assert persisted.wagon_number == WAGON_NUMBER
        assert persisted.part_number == "PN-42"
        assert persisted.description == "A description"

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
        await dp.feed_update(
            bot, make_callback_update(SeverityCB(value="critical").pack())
        )
        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))
        await dp.feed_update(bot, make_callback_update(CB_MEAS_DONE))
        await dp.feed_update(bot, make_message_update("A description"))
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
        assert await state.get_state() == DefectSG.employee_verdict.state

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
    """Hidden on the way in, since no step takes it for an answer; back on the way out."""

    async def test_the_way_in_hides_it(self, dp, bot, session, flow):
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))

        (sent,) = session.calls("sendMessage")
        assert sent.reply_markup == ReplyKeyboardRemove()

    @pytest.mark.parametrize(
        "step", [DefectSG.department, DefectSG.wagon_num], ids=["plain", "scene"]
    )
    async def test_the_cancel_button_brings_it_back(
        self, dp, bot, session, state, step
    ):
        """The scene leaves through exit(), whose action drops the form."""
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(step)

        await dp.feed_update(bot, make_callback_update(CB_CANCEL))

        (sent,) = session.calls("sendMessage")
        assert (sent.text, sent.reply_markup) == (
            str(M.DEFECT_CANCELLED),
            main_menu_keyboard(),
        )
        assert session.calls("editMessageReplyMarkup")
        assert await state.get_state() is None
        assert await load_defect(state) is None

    async def test_the_verdict_brings_it_back(self, dp, bot, session, state, flow):
        await save_defect(state, DefectData(wagon_id=3, defect_id=str(uuid.uuid4())))
        await state.set_state(DefectSG.employee_verdict)

        await dp.feed_update(
            bot, make_callback_update(VerdictCB(value=DefectVerdict.OK).pack())
        )

        assert session.calls("sendMessage")[-1].reply_markup == main_menu_keyboard()

    async def test_a_failed_save_brings_it_back(self, dp, bot, session, state, flow):
        flow.register.side_effect = RuntimeError("db down")
        await save_defect(state, DefectData(wagon_id=3))
        await state.set_state(DefectSG.confirm)

        await dp.feed_update(
            bot, make_callback_update(ConfirmCB(confirmed=True).pack())
        )

        (sent,) = session.calls("sendMessage")
        assert (sent.text, sent.reply_markup) == (
            str(M.SAVE_FAILED),
            main_menu_keyboard(),
        )
        assert await state.get_state() is None

    async def test_a_failed_verdict_brings_it_back(self, dp, bot, session, state, flow):
        flow.verdict_services.save_employee_verdict.side_effect = RuntimeError("down")
        await save_defect(state, DefectData(wagon_id=3, defect_id=str(uuid.uuid4())))
        await state.set_state(DefectSG.employee_verdict)

        await dp.feed_update(
            bot, make_callback_update(VerdictCB(value=DefectVerdict.OK).pack())
        )

        (sent,) = session.calls("sendMessage")
        assert (sent.text, sent.reply_markup) == (
            str(M.SESSION_ERROR),
            main_menu_keyboard(),
        )
        assert await state.get_state() is None


class TestFromTheWagonStepToTheDepartment:
    async def test_a_known_number_shows_the_department_step(
        self, dp, bot, session, state, flow
    ):
        """goto(): the department scene draws its own screen, as a new message."""
        await save_defect(state, DefectData())
        await state.set_state(DefectSG.wagon_num)

        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))

        (sent,) = session.calls("sendMessage")
        expected = build_wagon_confirmed_text(WAGON_NUMBER)
        assert (sent.text, sent.entities) == expected.render()
        assert sent.reply_markup == department_keyboard()
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
        expected = build_department_confirmed_text(Department.BOGIE.label)
        assert (edit.text, edit.entities) == expected.render()
        assert edit.reply_markup == node_keyboard_for_department(Department.BOGIE)
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
        assert edit.text == build_edit_node_text().render()[0]
        assert edit.reply_markup == node_keyboard_for_department(Department.BOGIE)
        assert await state.get_state() == DefectSG.node.state

    async def test_the_new_node_returns_to_the_summary(self, dp, bot, state):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.confirm)
        await dp.feed_update(bot, make_callback_update(EditCB(field="node").pack()))

        await dp.feed_update(
            bot, make_callback_update(NodeCB(value=DefectNode.WHEEL).pack())
        )

        assert await state.get_state() == DefectSG.confirm.state
        assert UD_EDITING not in await state.get_data()
        assert (await load_defect(state)).node == DefectNode.WHEEL


class TestThePartNumberStep:
    """Skip is an empty part number and a goto(); the next scene says it was skipped."""

    FORM = DefectData(wagon_id=1, department=Department.BOGIE, node_label="Wheel")

    async def test_the_node_leads_to_it_in_place(self, dp, bot, session, state):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.node)

        await dp.feed_update(
            bot, make_callback_update(NodeCB(value=DefectNode.WHEEL).pack())
        )

        (edit,) = session.calls("editMessageText")
        expected = build_node_confirmed_text(DefectNode.WHEEL.label)
        assert (edit.text, edit.entities) == expected.render()
        assert edit.reply_markup == skip_keyboard(CB_PART_NUMBER_SKIP)
        assert await state.get_state() == DefectSG.part_number.state

    async def test_skip_says_so_and_offers_the_types(self, dp, bot, session, state):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.part_number)

        await dp.feed_update(bot, make_callback_update(CB_PART_NUMBER_SKIP))

        (edit,) = session.calls("editMessageText")
        assert edit.text == build_part_number_skipped_text().render()[0]
        assert edit.reply_markup == defect_type_keyboard()
        assert await state.get_state() == DefectSG.defect_type.state
        assert (await load_defect(state)).part_number == ""

    async def test_a_typed_one_is_confirmed_as_typed(self, dp, bot, session, state):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.part_number)

        await dp.feed_update(bot, make_message_update("<PN-42>"))

        (sent,) = session.calls("sendMessage")
        expected = build_part_number_confirmed_text("<PN-42>")
        assert (sent.text, sent.entities) == expected.render()
        assert sent.reply_markup == defect_type_keyboard()
        assert (await load_defect(state)).part_number == "<PN-42>"

    async def test_skip_from_an_edit_clears_it_and_goes_back(self, dp, bot, state):
        await save_defect(state, DefectData(wagon_id=1, part_number="PN-1"))
        await state.set_state(DefectSG.confirm)
        tap = EditCB(field="part_number").pack()
        await dp.feed_update(bot, make_callback_update(tap))

        await dp.feed_update(bot, make_callback_update(CB_PART_NUMBER_SKIP))

        assert await state.get_state() == DefectSG.confirm.state
        assert UD_EDITING not in await state.get_data()
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
        assert edit.text == build_edit_defect_type_text().render()[0]
        assert await state.get_state() == DefectSG.defect_type.state

        tap = DefectTypeCB(value=DefectType.CRACK).pack()
        await dp.feed_update(bot, make_callback_update(tap))

        assert await state.get_state() == DefectSG.confirm.state
        assert (await load_defect(state)).defect_type == DefectType.CRACK


class TestTheSeverityStep:
    async def test_the_type_leads_to_it_in_place(self, dp, bot, session, state):
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.defect_type)

        tap = DefectTypeCB(value=DefectType.CRACK).pack()
        await dp.feed_update(bot, make_callback_update(tap))

        (edit,) = session.calls("editMessageText")
        expected = build_defect_type_confirmed_text(DefectType.CRACK.label)
        assert (edit.text, edit.entities) == expected.render()
        assert edit.reply_markup == severity_keyboard()
        assert await state.get_state() == DefectSG.severity.state

    async def test_it_leads_to_the_photo_step_in_place(self, dp, bot, session, state):
        """Skip until the first photo; the photo scene draws that itself."""
        await save_defect(state, DefectData(wagon_id=1))
        await state.set_state(DefectSG.severity)

        await dp.feed_update(bot, make_callback_update(SeverityCB(value="high").pack()))

        (edit,) = session.calls("editMessageText")
        expected = build_severity_confirmed_text(SEVERITY_LABELS["high"])
        assert (edit.text, edit.entities) == expected.render()
        assert edit.reply_markup == skip_keyboard(CB_PHOTO_SKIP)
        assert await state.get_state() == DefectSG.photo.state

    async def test_an_edit_asks_again_and_goes_back(self, dp, bot, session, state):
        await save_defect(state, DefectData(wagon_id=1, severity="low"))
        await state.set_state(DefectSG.confirm)

        await dp.feed_update(bot, make_callback_update(EditCB(field="severity").pack()))
        (edit,) = session.calls("editMessageText")
        assert edit.text == str(M.EDIT_SEVERITY)
        assert edit.reply_markup == severity_keyboard()

        await dp.feed_update(bot, make_callback_update(SeverityCB(value="high").pack()))

        assert await state.get_state() == DefectSG.confirm.state
        assert (await load_defect(state)).severity == "high"


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
        assert edits == [build_edit_wagon_text().render()[0]]
        assert await state.get_state() == DefectSG.wagon_num.state
        assert (await state.get_data())[UD_EDITING] is True

    async def test_the_new_number_returns_to_the_summary(
        self, dp, bot, session, state, flow
    ):
        await save_defect(state, self.FORM)
        await state.set_state(DefectSG.confirm)
        await dp.feed_update(bot, make_callback_update(EditCB(field="wagon").pack()))

        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))

        assert await state.get_state() == DefectSG.confirm.state
        assert UD_EDITING not in await state.get_data()
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
        from apps.bot.constants import UD_DEFECT
        from apps.bot.user_data import STATE_SCHEMA_VERSION

        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await dp.feed_update(bot, make_message_update(WAGON_NUMBER))
        await dp.feed_update(
            bot, make_callback_update(DepartmentCB(value=Department.BOGIE).pack())
        )
        assert await state.get_state() == DefectSG.node.state

        stored = (await state.get_data())[UD_DEFECT]
        stored["_schema"] = STATE_SCHEMA_VERSION + 1
        await state.update_data({UD_DEFECT: stored})

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
        assert [m.text for m in sent] == [str(M.FORM_OUTDATED)]
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
        from apps.bot.constants import UD_DEFECT

        await self._mid_flow_with_a_foreign_schema(dp, bot, state)
        await state.set_state(None)
        session.clear()

        await dp.feed_update(bot, make_message_update("/help", command=True))

        assert [m.text for m in session.calls("sendMessage")] == [
            build_help_text().render()[0]
        ]
        assert UD_DEFECT not in await state.get_data()


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
        assert sent == [str(M.DEFECT_CANCELLED)]
        assert await state.get_state() is None

    async def test_a_tap_ends_it_too(self, dp, bot, session, state):
        await state.set_state(DefectSG.measurement_dimension)
        tap = DimensionCB(value=MeasurementDimension.DEPTH).pack()

        await dp.feed_update(bot, make_callback_update(tap))

        sent = [m.text for m in session.calls("sendMessage")]
        assert sent == [str(M.DEFECT_CANCELLED)]
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
    async def test_the_pick_is_named_on_the_severity_screen(
        self, dp, bot, session, state
    ):
        await self._up_to_the_type(dp, bot)

        await dp.feed_update(
            bot, make_callback_update(ResponsibleEmployeeCB(employee_id=1).pack())
        )

        assert await state.get_state() == DefectSG.severity.state
        assert (await load_defect(state)).responsible_employee_label == "U1 L"
        edit = session.calls("editMessageText")[-1]
        expected = build_responsible_employee_confirmed_text("U1 L")
        assert (edit.text, edit.entities) == expected.render()
        assert edit.reply_markup == severity_keyboard()

    @pytest.mark.usefixtures("flow", "roster")
    async def test_skipped_it_goes_on_through_the_photos_to_the_description(
        self, dp, bot, state
    ):
        """No measurements for a human factor."""
        await self._up_to_the_type(dp, bot)

        await dp.feed_update(bot, make_callback_update(CB_RESP_EMP_SKIP))
        assert await state.get_state() == DefectSG.severity.state

        await dp.feed_update(
            bot, make_callback_update(SeverityCB(value="critical").pack())
        )
        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))

        assert await state.get_state() == DefectSG.desc.state
        assert (await load_defect(state)).responsible_employee_id is None

    @pytest.mark.usefixtures("flow")
    async def test_a_typed_name_narrows_the_list_in_a_new_message(
        self, dp, bot, session, state, roster
    ):
        await self._up_to_the_type(dp, bot)
        session.clear()

        await dp.feed_update(bot, make_message_update("U1"))

        roster.assert_awaited_with(
            Department.BOGIE, "U1", limit=EMPLOYEE_PAGE_SIZE, offset=0
        )
        (sent,) = session.calls("sendMessage")
        assert "U1" in sent.text
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
        assert UD_EDITING not in await state.get_data()
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
        assert UD_EDITING not in await state.get_data()
        assert (await load_defect(state)).responsible_employee_id == 1
        assert "U1 L" in session.calls("editMessageText")[-1].text


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
        await dp.feed_update(
            bot, make_callback_update(SeverityCB(value="critical").pack())
        )
        assert await state.get_state() == DefectSG.photo.state

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
        answers = session.calls("sendMessage")
        assert [a.text for a in answers] == [build_album_receiving_text().render()[0]]

        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))

        toast = session.calls("answerCallbackQuery")[-1]
        assert toast.text == build_photos_attached_toast(3)
        assert await state.get_state() == DefectSG.measurement_choice.state

    async def test_a_lone_photo_is_acknowledged_immediately(
        self, dp, bot, session, state, flow
    ):
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await state.set_state(DefectSG.photo)
        session.clear()

        await dp.feed_update(bot, make_photo_update("solo"))

        assert len(session.calls("sendMessage")) == 1
