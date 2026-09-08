from unittest.mock import AsyncMock, MagicMock, patch

from telegram.ext import ConversationHandler

from apps.bot.callbacks import (
    DepartmentCB,
    PartNumberSkipCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    ResponsibleEmployeeSkipCB,
)
from apps.bot.constants import (
    UD_DEFECT,
    UD_RESP_EMPLOYEES,
    UD_RESP_SEARCH,
)
from apps.bot.handlers.common.cancel import cancel
from apps.bot.handlers.common.help import help_command
from apps.bot.handlers.defect.defect_type import receive_defect_type
from apps.bot.handlers.defect.department import receive_department
from apps.bot.handlers.defect.node import receive_node
from apps.bot.handlers.defect.part_number import (
    receive_part_number,
    skip_part_number,
)
from apps.bot.handlers.defect.responsible_employee import (
    page_responsible_employee,
    search_responsible_employee,
    select_responsible_employee,
    skip_responsible_employee,
)
from apps.bot.handlers.defect.responsible_employee.list import _filter_and_page
from apps.bot.messages import BotMessages as M
from apps.bot.states import (
    DEFECT_TYPE,
    DESC,
    NODE,
    PART_NUMBER,
    RESPONSIBLE_EMPLOYEE,
    SEVERITY,
)
from apps.bot.tests.builders import make_message as _make_message
from apps.bot.user_data import DefectData
from apps.defects.constants import DefectType

RESP_EMP_PAGE_SIZE = 5


def _make_cb_update(cb_data):
    update = MagicMock()
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.data = cb_data
    update.message = None
    return update


def _make_msg_update(text="ABC-123"):
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.callback_query = None
    return update


def _make_employee(pk=1, first="Bat", last="Erdene"):
    e = MagicMock()
    e.id = pk
    e.first_name = first
    e.last_name = last
    return e


class TestCancelHandler:
    async def test_clears_everything_the_conversation_stored(self, state):
        await state.set_state("DefectSG:node")
        await state.update_data({UD_DEFECT: {"node": "wheel"}})

        await cancel(_make_message(), state)

        assert await state.get_data() == {}
        assert await state.get_state() is None

    async def test_replies_with_cancelled_message(self, state):
        message = _make_message()

        await cancel(message, state)

        message.answer.assert_awaited_once_with(
            str(M.CANCELLED), parse_mode=M.PARSE_MODE
        )

    async def test_tolerates_an_idle_conversation(self, state):
        await cancel(_make_message(), state)

        assert await state.get_state() is None


class TestHelpHandler:
    async def test_replies_with_help_text(self):
        message = _make_message()

        await help_command(message)

        message.answer.assert_awaited_once_with(
            str(M.HELP_TEXT), parse_mode=M.PARSE_MODE
        )


class TestReceiveDepartment:
    async def test_saves_department_to_defect_data(self, mock_context):
        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        update = _make_cb_update(DepartmentCB(value="bogie"))

        await receive_department(update, mock_context)

        assert defect.department == "bogie"

    async def test_saves_department_label(self, mock_context):
        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        update = _make_cb_update(DepartmentCB(value="bogie"))

        await receive_department(update, mock_context)

        assert defect.department_label is not None
        assert len(defect.department_label) > 0

    async def test_returns_node_state(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(DepartmentCB(value="bogie"))

        result = await receive_department(update, mock_context)

        assert result == NODE

    async def test_edits_message(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(DepartmentCB(value="wheelset"))

        await receive_department(update, mock_context)

        update.callback_query.edit_message_text.assert_called_once()


class TestReceiveNode:
    async def test_saves_node_to_defect_data(self, mock_context):
        from apps.bot.callbacks import NodeCB

        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        update = _make_cb_update(NodeCB(value="wheel"))

        await receive_node(update, mock_context)

        assert defect.node == "wheel"

    async def test_returns_part_number_state(self, mock_context):
        from apps.bot.callbacks import NodeCB

        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(NodeCB(value="axle"))

        result = await receive_node(update, mock_context)

        assert result == PART_NUMBER


class TestReceivePartNumber:
    async def test_text_input_saves_part_number(self, mock_context):
        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        update = _make_msg_update("ABC-1234")

        await receive_part_number(update, mock_context)

        assert defect.part_number == "ABC-1234"

    async def test_text_input_returns_defect_type_state(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_msg_update("P-001")

        result = await receive_part_number(update, mock_context)

        assert result == DEFECT_TYPE

    async def test_skip_clears_part_number(self, mock_context):
        defect = DefectData(part_number="old")
        mock_context.user_data[UD_DEFECT] = defect
        update = _make_cb_update(PartNumberSkipCB())

        await skip_part_number(update, mock_context)

        assert defect.part_number == ""

    async def test_skip_returns_defect_type_state(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(PartNumberSkipCB())

        result = await skip_part_number(update, mock_context)

        assert result == DEFECT_TYPE


class TestReceiveDefectType:
    async def test_human_factor_returns_severity_state(self, mock_context):
        from apps.bot.callbacks import DefectTypeCB

        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(DefectTypeCB(value=DefectType.HUMAN_FACTOR))

        result = await receive_defect_type(update, mock_context)

        assert result == SEVERITY

    async def test_human_factor_shows_severity_keyboard(self, mock_context):
        from apps.bot.callbacks import DefectTypeCB, SeverityCB

        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(DefectTypeCB(value=DefectType.HUMAN_FACTOR))

        await receive_defect_type(update, mock_context)

        buttons = [
            btn
            for row in update.callback_query.edit_message_text.call_args.kwargs[
                "reply_markup"
            ].inline_keyboard
            for btn in row
        ]
        assert any(isinstance(btn.callback_data, SeverityCB) for btn in buttons)

    async def test_other_type_returns_severity_state(self, mock_context):
        from apps.bot.callbacks import DefectTypeCB

        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(DefectTypeCB(value=DefectType.CRACK))

        result = await receive_defect_type(update, mock_context)

        assert result == SEVERITY

    async def test_saves_defect_type(self, mock_context):
        from apps.bot.callbacks import DefectTypeCB

        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        update = _make_cb_update(DefectTypeCB(value=DefectType.WEAR))

        await receive_defect_type(update, mock_context)

        assert defect.defect_type == DefectType.WEAR


class TestFilterAndPage:
    def _employees(self, names):
        return [_make_employee(i, *n.split()) for i, n in enumerate(names, 1)]

    def test_returns_all_when_no_search(self):
        emps = self._employees(
            ["Erdenebayar Soyolerdene", "Lionel Messi", "Sigourney Weaver"]
        )
        page_emps, total, total_pages, page = _filter_and_page(emps, "", 0)
        assert total == 3
        assert len(page_emps) == 3

    def test_filters_by_first_name(self):
        emps = self._employees(
            ["Erdenebayar Soyolerdene", "Lionel Messi", "Sigourney Weaver"]
        )
        page_emps, total, _, _ = _filter_and_page(emps, "Erdenebayar", 0)
        assert total == 1

    def test_filters_case_insensitive(self):
        emps = self._employees(
            [
                "Erdenebayar Soyolerdene",
                "Soyolerdene Erdenebayar",
            ]
        )
        _, total, _, _ = _filter_and_page(emps, "erdenebayar", 0)
        assert total == 2

    def test_pagination_returns_correct_page_size(self):
        emps = self._employees([f"User{i} Last{i}" for i in range(12)])
        page_emps, total, total_pages, page = _filter_and_page(emps, "", 0)
        assert len(page_emps) == RESP_EMP_PAGE_SIZE
        assert total == 12
        assert total_pages == 3

    def test_second_page(self):
        emps = self._employees([f"User{i} Last{i}" for i in range(12)])
        page_emps, _, _, page = _filter_and_page(emps, "", 1)
        assert page == 1
        assert len(page_emps) == RESP_EMP_PAGE_SIZE

    def test_page_clamped_to_max(self):
        emps = self._employees(["A B", "C D"])
        _, _, total_pages, page = _filter_and_page(emps, "", 99)
        assert page == total_pages - 1

    def test_empty_list_returns_one_page(self):
        _, total, total_pages, page = _filter_and_page([], "", 0)
        assert total == 0
        assert total_pages == 1
        assert page == 0


class TestReceiveResponsibleEmployee:
    async def test_skip_returns_desc_state(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        mock_context.user_data[UD_RESP_EMPLOYEES] = []
        mock_context.user_data[UD_RESP_SEARCH] = ""
        update = _make_cb_update(ResponsibleEmployeeSkipCB())

        result = await skip_responsible_employee(update, mock_context)

        assert result == DESC

    async def test_skip_clears_employee(self, mock_context):
        defect = DefectData(responsible_employee_id=5, responsible_employee_label="X Y")
        mock_context.user_data[UD_DEFECT] = defect
        mock_context.user_data[UD_RESP_EMPLOYEES] = []
        update = _make_cb_update(ResponsibleEmployeeSkipCB())

        await skip_responsible_employee(update, mock_context)

        assert defect.responsible_employee_id is None
        assert defect.responsible_employee_label is None

    async def test_skip_clears_temp_user_data(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        mock_context.user_data[UD_RESP_EMPLOYEES] = [_make_employee()]
        mock_context.user_data[UD_RESP_SEARCH] = "foo"
        update = _make_cb_update(ResponsibleEmployeeSkipCB())

        await skip_responsible_employee(update, mock_context)

        assert UD_RESP_EMPLOYEES not in mock_context.user_data
        assert UD_RESP_SEARCH not in mock_context.user_data

    async def test_page_nav_returns_responsible_employee_state(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        mock_context.user_data[UD_RESP_EMPLOYEES] = [
            _make_employee(i, f"U{i}", "L") for i in range(10)
        ]
        mock_context.user_data[UD_RESP_SEARCH] = ""
        update = _make_cb_update(ResponsibleEmployeePageCB(page=1))

        result = await page_responsible_employee(update, mock_context)

        assert result == RESPONSIBLE_EMPLOYEE

    async def test_select_employee_saves_id(self, mock_context):
        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        mock_context.user_data[UD_RESP_EMPLOYEES] = []
        update = _make_cb_update(ResponsibleEmployeeCB(employee_id=7))

        emp = _make_employee(7, "Bold", "Bat")
        with patch(
            "asgiref.sync.sync_to_async",
            return_value=AsyncMock(return_value=emp),
        ):
            result = await select_responsible_employee(update, mock_context)

        assert defect.responsible_employee_id == 7
        assert result == DESC

    async def test_select_employee_clears_temp_user_data(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        mock_context.user_data[UD_RESP_EMPLOYEES] = [_make_employee()]
        mock_context.user_data[UD_RESP_SEARCH] = "query"
        update = _make_cb_update(ResponsibleEmployeeCB(employee_id=1))

        emp = _make_employee(1, "A", "B")
        with patch(
            "asgiref.sync.sync_to_async",
            return_value=AsyncMock(return_value=emp),
        ):
            await select_responsible_employee(update, mock_context)

        assert UD_RESP_EMPLOYEES not in mock_context.user_data
        assert UD_RESP_SEARCH not in mock_context.user_data


class TestSearchResponsibleEmployee:
    async def test_updates_search_query(self, mock_context):
        mock_context.user_data[UD_RESP_EMPLOYEES] = [
            _make_employee(1, "Bold", "Bindariya")
        ]
        mock_context.user_data[UD_RESP_SEARCH] = ""
        update = _make_msg_update("Bold")

        await search_responsible_employee(update, mock_context)

        assert mock_context.user_data[UD_RESP_SEARCH] == "Bold"

    async def test_returns_responsible_employee_state(self, mock_context):
        mock_context.user_data[UD_RESP_EMPLOYEES] = []
        mock_context.user_data[UD_RESP_SEARCH] = ""
        update = _make_msg_update("test")

        result = await search_responsible_employee(update, mock_context)

        assert result == RESPONSIBLE_EMPLOYEE


class TestEditFromSummary:
    async def test_start_edit_sets_flag_and_routes_to_field(self, mock_context):
        from apps.bot.callbacks import EditCB
        from apps.bot.constants import UD_EDITING
        from apps.bot.handlers.defect.edit import start_edit

        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(EditCB(field="severity"))

        result = await start_edit(update, mock_context)

        assert result == SEVERITY
        assert mock_context.user_data[UD_EDITING] is True

    async def test_start_edit_unknown_field_returns_confirm(self, mock_context):
        from apps.bot.callbacks import EditCB
        from apps.bot.constants import UD_EDITING
        from apps.bot.handlers.defect.edit import start_edit
        from apps.bot.states import CONFIRM

        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(EditCB(field="nope"))

        result = await start_edit(update, mock_context)

        assert result == CONFIRM
        assert UD_EDITING not in mock_context.user_data

    async def test_field_handler_in_edit_mode_returns_to_summary(self, mock_context):
        from apps.bot.callbacks import DefectTypeCB
        from apps.bot.constants import UD_EDITING
        from apps.bot.states import CONFIRM

        mock_context.user_data[UD_DEFECT] = DefectData()
        mock_context.user_data[UD_EDITING] = True
        update = _make_cb_update(DefectTypeCB(value=DefectType.HUMAN_FACTOR))

        result = await receive_defect_type(update, mock_context)

        assert result == CONFIRM
        assert UD_EDITING not in mock_context.user_data


class TestUnlinkedEmployeeIsRefused:
    """The employee is read per update, so a revoked one must be stopped."""

    async def test_confirm_saves_nothing_without_an_employee(self, mock_context):
        from apps.bot.callbacks import ConfirmCB
        from apps.bot.handlers.defect.confirm.handler import confirm_defect

        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(ConfirmCB(confirmed=True))

        with (
            patch(
                "apps.bot.handlers.defect.confirm.handler.get_employee",
                AsyncMock(return_value=None),
            ),
            patch(
                "apps.bot.handlers.defect.confirm.handler.register_defect",
                new_callable=AsyncMock,
            ) as save,
        ):
            result = await confirm_defect(update, mock_context)

        save.assert_not_awaited()
        assert result == ConversationHandler.END

    async def test_verdict_is_not_recorded_without_an_employee(self, mock_context):
        from apps.bot.callbacks import VerdictCB
        from apps.bot.handlers.defect.verdict import receive_employee_verdict
        from apps.defects.constants import DefectVerdict

        mock_context.user_data[UD_DEFECT] = DefectData(defect_id="1")
        update = _make_cb_update(VerdictCB(value=DefectVerdict.DECOMMISSION))

        with (
            patch(
                "apps.bot.handlers.defect.verdict.get_employee",
                AsyncMock(return_value=None),
            ),
            patch("apps.bot.handlers.defect.verdict.services") as svc,
        ):
            result = await receive_employee_verdict(update, mock_context)

        svc.save_employee_verdict.assert_not_called()
        assert result == ConversationHandler.END


class TestAfterPhotosStoresSerializableEmployees:
    """The roster is parked in user_data, so it must not hold live ORM objects."""

    async def test_stores_employee_refs_not_model_instances(self, mock_context):
        from apps.bot.handlers.defect.photo.routing import after_photos
        from apps.bot.user_data import EmployeeRef

        defect = DefectData(
            defect_type=DefectType.HUMAN_FACTOR, department="coupler_brake"
        )
        msg = MagicMock()
        msg.reply_text = AsyncMock()

        with (
            patch(
                "apps.bot.services.get_employees_by_department",
                AsyncMock(return_value=[_make_employee(7, "Ivan", "Petrov")]),
            ),
            patch(
                "apps.bot.handlers.defect.responsible_employee"
                ".show_responsible_employee_list",
                AsyncMock(),
            ),
        ):
            result = await after_photos(msg, defect, mock_context, edit=False)

        stored = mock_context.user_data[UD_RESP_EMPLOYEES]
        assert stored == [EmployeeRef(id=7, first_name="Ivan", last_name="Petrov")]
        assert result == RESPONSIBLE_EMPLOYEE

    async def test_stored_roster_is_json_serializable(self, mock_context):
        import json

        from apps.bot.handlers.defect.photo.routing import after_photos

        defect = DefectData(
            defect_type=DefectType.HUMAN_FACTOR, department="coupler_brake"
        )
        msg = MagicMock()
        msg.reply_text = AsyncMock()

        with (
            patch(
                "apps.bot.services.get_employees_by_department",
                AsyncMock(return_value=[_make_employee(7, "Ivan", "Petrov")]),
            ),
            patch(
                "apps.bot.handlers.defect.responsible_employee"
                ".show_responsible_employee_list",
                AsyncMock(),
            ),
        ):
            await after_photos(msg, defect, mock_context, edit=False)

        roster = mock_context.user_data[UD_RESP_EMPLOYEES]
        assert json.dumps([ref.to_dict() for ref in roster])


class TestMeasurementChoice:
    """Add and skip/done were one handler branching on the callback type."""

    async def test_add_starts_a_measurement_and_asks_for_the_dimension(
        self, mock_context
    ):
        from apps.bot.callbacks import MeasurementAddCB
        from apps.bot.handlers.defect.measurement import measurement_add
        from apps.bot.states import MEASUREMENT_DIMENSION
        from apps.bot.user_data import MeasurementEntry

        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        update = _make_cb_update(MeasurementAddCB())

        result = await measurement_add(update, mock_context)

        assert defect.current_measurement == MeasurementEntry()
        assert result == MEASUREMENT_DIMENSION
        update.callback_query.answer.assert_awaited_once()

    async def test_done_moves_on_to_the_description(self, mock_context):
        from apps.bot.callbacks import MeasurementDoneCB
        from apps.bot.handlers.defect.measurement import measurement_done

        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        update = _make_cb_update(MeasurementDoneCB())

        result = await measurement_done(update, mock_context)

        assert result == DESC
        assert defect.current_measurement is None

    async def test_skip_takes_the_same_path_as_done(self, mock_context):
        from apps.bot.callbacks import MeasurementSkipCB
        from apps.bot.handlers.defect.measurement import measurement_done

        mock_context.user_data[UD_DEFECT] = DefectData()
        update = _make_cb_update(MeasurementSkipCB())

        result = await measurement_done(update, mock_context)

        assert result == DESC

    async def test_done_does_not_need_a_defect_in_state(self, mock_context):
        from apps.bot.callbacks import MeasurementDoneCB
        from apps.bot.handlers.defect.measurement import measurement_done

        update = _make_cb_update(MeasurementDoneCB())

        assert await measurement_done(update, mock_context) == DESC
