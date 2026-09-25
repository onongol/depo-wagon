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
    CB_MEAS_ADD,
    CB_MEAS_DONE,
    CB_PHOTO_SKIP,
    CB_RESP_EMP_SKIP,
    ConfirmCB,
    DefectTypeCB,
    DepartmentCB,
    DimensionCB,
    NodeCB,
    SeverityCB,
    VerdictCB,
)
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.common.text import build_help_text
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
        edits = session.calls("editMessageText")
        assert [e.text for e in edits] == [str(M.FORM_OUTDATED)]

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

        edits = [e.text for e in session.calls("editMessageText")]
        assert edits == [str(M.DEFECT_CANCELLED)]
        assert await state.get_state() is None


class TestHumanFactorBranch:
    async def test_routes_to_the_employee_picker(self, dp, bot, state, flow):
        roster = [MagicMock(id=i, first_name=f"U{i}", last_name="L") for i in range(3)]

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
            bot,
            make_callback_update(DefectTypeCB(value=DefectType.HUMAN_FACTOR).pack()),
        )
        await dp.feed_update(
            bot, make_callback_update(SeverityCB(value="critical").pack())
        )

        with (
            patch(
                "apps.bot.services.count_department_employees",
                AsyncMock(return_value=len(roster)),
            ),
            patch(
                "apps.bot.services.get_department_employees",
                AsyncMock(return_value=roster),
            ),
        ):
            await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))

        assert await state.get_state() == DefectSG.responsible_employee.state

        await dp.feed_update(bot, make_callback_update(CB_RESP_EMP_SKIP))
        assert await state.get_state() == DefectSG.desc.state


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
        assert [a.text for a in answers] == [str(M.PHOTO_ALBUM_RECEIVING)]

        await dp.feed_update(bot, make_callback_update(CB_PHOTO_SKIP))

        toast = session.calls("answerCallbackQuery")[-1]
        assert toast.text == str(M.PHOTOS_ATTACHED).format(count=3)
        assert await state.get_state() == DefectSG.measurement_choice.state

    async def test_a_lone_photo_is_acknowledged_immediately(
        self, dp, bot, session, state, flow
    ):
        await dp.feed_update(bot, make_message_update("/new_defect", command=True))
        await state.set_state(DefectSG.photo)
        session.clear()

        await dp.feed_update(bot, make_photo_update("solo"))

        assert len(session.calls("sendMessage")) == 1
