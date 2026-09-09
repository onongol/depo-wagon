"""Tests for the defect registration steps and the shared utility handlers.

Every step now round-trips its form through storage, so a loaded DefectData is
a detached copy — the assertions read it back rather than holding a reference.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from apps.bot.callback_data import (
    DefectTypeCB,
    DepartmentCB,
    EditCB,
    NodeCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    SeverityCB,
)
from apps.bot.constants import UD_DEFECT, UD_EDITING, UD_RESP_EMPLOYEES, UD_RESP_SEARCH
from apps.bot.fsm import load_defect, save_defect, save_employees
from apps.bot.handlers.common.cancel import cancel
from apps.bot.handlers.common.help import help_command
from apps.bot.handlers.defect.defect_type import receive_defect_type
from apps.bot.handlers.defect.department import receive_department
from apps.bot.handlers.defect.edit import start_edit
from apps.bot.handlers.defect.node import receive_node
from apps.bot.handlers.defect.part_number import receive_part_number, skip_part_number
from apps.bot.handlers.defect.responsible_employee import (
    page_responsible_employee,
    search_responsible_employee,
    select_responsible_employee,
    skip_responsible_employee,
)
from apps.bot.handlers.defect.responsible_employee.list import _filter_and_page
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.tests.builders import make_callback, make_message
from apps.bot.user_data import DefectData, EmployeeRef
from apps.defects.constants import DefectType

EMPLOYEE_PAGE_SIZE = 5


def _make_employee(pk=1, first="Bat", last="Erdene"):
    return EmployeeRef(id=pk, first_name=first, last_name=last)


class TestCancelHandler:
    async def test_clears_everything_the_conversation_stored(self, state):
        await state.set_state(DefectSG.node)
        await state.update_data({UD_DEFECT: {"node": "wheel"}})

        await cancel(make_message(), state)

        assert await state.get_data() == {}
        assert await state.get_state() is None

    async def test_replies_with_cancelled_message(self, state):
        message = make_message()

        await cancel(message, state)

        message.answer.assert_awaited_once_with(
            str(M.CANCELLED), parse_mode=M.PARSE_MODE
        )

    async def test_tolerates_an_idle_conversation(self, state):
        await cancel(make_message(), state)

        assert await state.get_state() is None


class TestHelpHandler:
    async def test_replies_with_help_text(self):
        message = make_message()

        await help_command(message)

        message.answer.assert_awaited_once_with(
            str(M.HELP_TEXT), parse_mode=M.PARSE_MODE
        )


class TestReceiveDepartment:
    async def test_saves_department_and_its_label(self, state):
        await save_defect(state, DefectData())

        await receive_department(make_callback(), DepartmentCB(value="bogie"), state)

        defect = await load_defect(state)
        assert defect.department == "bogie"
        assert defect.department_label

    async def test_moves_to_the_node_step(self, state):
        await save_defect(state, DefectData())

        await receive_department(make_callback(), DepartmentCB(value="bogie"), state)

        assert await state.get_state() == DefectSG.node.state

    async def test_edits_the_message_in_place(self, state):
        await save_defect(state, DefectData())
        callback = make_callback()

        await receive_department(callback, DepartmentCB(value="bogie"), state)

        callback.message.edit_text.assert_awaited_once()


class TestReceiveNode:
    async def test_saves_node_and_its_label(self, state):
        await save_defect(state, DefectData())

        await receive_node(make_callback(), NodeCB(value="wheel"), state)

        defect = await load_defect(state)
        assert defect.node == "wheel"
        assert defect.node_label

    async def test_moves_to_the_part_number_step(self, state):
        await save_defect(state, DefectData())

        await receive_node(make_callback(), NodeCB(value="wheel"), state)

        assert await state.get_state() == DefectSG.part_number.state


class TestReceivePartNumber:
    async def test_text_input_saves_the_part_number(self, state):
        await save_defect(state, DefectData())

        await receive_part_number(make_message("ABC-1234"), state)

        assert (await load_defect(state)).part_number == "ABC-1234"

    async def test_text_input_moves_to_the_defect_type_step(self, state):
        await save_defect(state, DefectData())

        await receive_part_number(make_message("P-001"), state)

        assert await state.get_state() == DefectSG.defect_type.state

    async def test_skip_clears_the_part_number(self, state):
        await save_defect(state, DefectData(part_number="old"))

        await skip_part_number(make_callback(), state)

        assert (await load_defect(state)).part_number == ""

    async def test_skip_moves_to_the_defect_type_step(self, state):
        await save_defect(state, DefectData())

        await skip_part_number(make_callback(), state)

        assert await state.get_state() == DefectSG.defect_type.state

    async def test_an_abandoned_form_ends_the_flow(self, state):
        message = make_message("ABC")

        await receive_part_number(message, state)

        message.answer.assert_awaited_once_with(str(M.DEFECT_CANCELLED))
        assert await state.get_state() is None


class TestReceiveDefectType:
    async def test_saves_the_type_and_moves_to_severity(self, state):
        await save_defect(state, DefectData())

        await receive_defect_type(
            make_callback(), DefectTypeCB(value=DefectType.HUMAN_FACTOR), state
        )

        assert (await load_defect(state)).defect_type == DefectType.HUMAN_FACTOR
        assert await state.get_state() == DefectSG.severity.state

    async def test_offers_the_severity_keyboard(self, state):
        await save_defect(state, DefectData())
        callback = make_callback()

        await receive_defect_type(
            callback, DefectTypeCB(value=DefectType.HUMAN_FACTOR), state
        )

        kb = callback.message.edit_text.await_args.kwargs["reply_markup"]
        payloads = [b.callback_data for row in kb.inline_keyboard for b in row]
        assert any(p.startswith(SeverityCB.__prefix__ + ":") for p in payloads)

    async def test_every_type_reaches_the_same_step(self, state):
        for value in DefectType.values:
            await save_defect(state, DefectData())
            await receive_defect_type(make_callback(), DefectTypeCB(value=value), state)
            assert await state.get_state() == DefectSG.severity.state


class TestFilterAndPage:
    def _employees(self, *names):
        return [_make_employee(i, *n.split()) for i, n in enumerate(names, 1)]

    def test_returns_all_when_no_search(self):
        emps = self._employees("Bat Erdene", "Bold Bat")

        page, total, _pages, _no = _filter_and_page(emps, "", 0)

        assert total == 2
        assert len(page) == 2

    def test_filters_by_first_name(self):
        emps = self._employees("Bat Erdene", "Bold Bat")

        page, total, _pages, _no = _filter_and_page(emps, "Bold", 0)

        assert total == 1
        assert page[0].first_name == "Bold"

    def test_filters_case_insensitive(self):
        emps = self._employees("Bat Erdene")

        _page, total, _pages, _no = _filter_and_page(emps, "bAt", 0)

        assert total == 1

    def test_pagination_returns_correct_page_size(self):
        emps = self._employees(*[f"N{i} L{i}" for i in range(12)])

        page, total, pages, _no = _filter_and_page(emps, "", 0)

        assert len(page) == EMPLOYEE_PAGE_SIZE
        assert total == 12
        assert pages == 3

    def test_second_page(self):
        emps = self._employees(*[f"N{i} L{i}" for i in range(12)])

        page, _total, _pages, page_no = _filter_and_page(emps, "", 1)

        assert page_no == 1
        assert len(page) == EMPLOYEE_PAGE_SIZE

    def test_page_clamped_to_max(self):
        emps = self._employees(*[f"N{i} L{i}" for i in range(6)])

        _page, _total, _pages, page_no = _filter_and_page(emps, "", 99)

        assert page_no == 1

    def test_empty_list_returns_one_page(self):
        _page, total, pages, page_no = _filter_and_page([], "", 0)

        assert total == 0
        assert pages == 1
        assert page_no == 0


class TestResponsibleEmployee:
    async def _seed(self, state, employees=()):
        await save_defect(state, DefectData())
        await save_employees(state, list(employees))
        await state.update_data({UD_RESP_SEARCH: ""})

    async def test_skip_moves_to_the_description(self, state):
        await self._seed(state)

        await skip_responsible_employee(make_callback(), state)

        assert await state.get_state() == DefectSG.desc.state

    async def test_skip_records_no_employee(self, state):
        await save_defect(
            state,
            DefectData(responsible_employee_id=5, responsible_employee_label="X Y"),
        )

        await skip_responsible_employee(make_callback(), state)

        defect = await load_defect(state)
        assert defect.responsible_employee_id is None
        assert defect.responsible_employee_label is None

    async def test_skip_drops_the_cached_roster(self, state):
        await self._seed(state, [_make_employee()])
        await state.update_data({UD_RESP_SEARCH: "foo"})

        await skip_responsible_employee(make_callback(), state)

        data = await state.get_data()
        assert UD_RESP_EMPLOYEES not in data
        assert UD_RESP_SEARCH not in data

    async def test_paging_leaves_the_step_where_it_is(self, state):
        await self._seed(state, [_make_employee(i, f"U{i}", "L") for i in range(10)])
        await state.set_state(DefectSG.responsible_employee)

        await page_responsible_employee(
            make_callback(), ResponsibleEmployeePageCB(page=1), state
        )

        assert await state.get_state() == DefectSG.responsible_employee.state

    async def test_select_records_the_employee(self, state):
        await self._seed(state, [_make_employee(7, "Bold", "Bat")])

        await select_responsible_employee(
            make_callback(), ResponsibleEmployeeCB(employee_id=7), state
        )

        defect = await load_defect(state)
        assert defect.responsible_employee_id == 7
        assert defect.responsible_employee_label == "Bold Bat"
        assert await state.get_state() == DefectSG.desc.state

    async def test_select_falls_back_to_the_id_when_the_roster_is_gone(self, state):
        await self._seed(state)

        await select_responsible_employee(
            make_callback(), ResponsibleEmployeeCB(employee_id=7), state
        )

        assert (await load_defect(state)).responsible_employee_label == "7"

    async def test_select_drops_the_cached_roster(self, state):
        await self._seed(state, [_make_employee()])
        await state.update_data({UD_RESP_SEARCH: "query"})

        await select_responsible_employee(
            make_callback(), ResponsibleEmployeeCB(employee_id=1), state
        )

        data = await state.get_data()
        assert UD_RESP_EMPLOYEES not in data
        assert UD_RESP_SEARCH not in data


class TestSearchResponsibleEmployee:
    async def test_stores_the_query(self, state):
        await save_employees(state, [_make_employee(1, "Bold", "Bindariya")])

        await search_responsible_employee(make_message("Bold"), state)

        assert (await state.get_data())[UD_RESP_SEARCH] == "Bold"

    async def test_leaves_the_step_where_it_is(self, state):
        await save_employees(state, [])
        await state.set_state(DefectSG.responsible_employee)

        await search_responsible_employee(make_message("test"), state)

        assert await state.get_state() == DefectSG.responsible_employee.state

    async def test_re_renders_as_a_new_message(self, state):
        await save_employees(state, [])
        message = make_message("test")

        await search_responsible_employee(message, state)

        message.answer.assert_awaited_once()


class TestEditFromSummary:
    async def test_routes_to_the_field_and_flags_edit_mode(self, state):
        await save_defect(state, DefectData(department="bogie"))

        await start_edit(make_callback(), EditCB(field="node"), state)

        assert (await state.get_data())[UD_EDITING] is True
        assert await state.get_state() == DefectSG.node.state

    async def test_an_unknown_field_returns_to_the_summary(self, state):
        await save_defect(state, DefectData())

        await start_edit(make_callback(), EditCB(field="nope"), state)

        assert await state.get_state() == DefectSG.confirm.state
        assert UD_EDITING not in await state.get_data()

    async def test_an_abandoned_form_ends_the_flow(self, state):
        callback = make_callback()

        await start_edit(callback, EditCB(field="node"), state)

        callback.message.edit_text.assert_awaited_once_with(str(M.DEFECT_CANCELLED))
        assert await state.get_state() is None

    async def test_the_edited_field_returns_to_the_summary(self, state):
        await save_defect(state, DefectData(department="bogie"))
        await start_edit(make_callback(), EditCB(field="node"), state)

        await receive_node(make_callback(), NodeCB(value="wheel"), state)

        assert await state.get_state() == DefectSG.confirm.state
        assert UD_EDITING not in await state.get_data()


class TestUnlinkedEmployeeIsRefused:
    """What the web revokes, the bot stops honouring — including mid-flow."""

    async def test_confirm_saves_nothing_without_an_employee(self, state, bot):
        from apps.bot.callback_data import ConfirmCB
        from apps.bot.handlers.defect.confirm import confirm_defect

        await save_defect(state, DefectData(wagon_id=1))

        with (
            patch(
                "apps.bot.handlers.defect.confirm.handler.get_employee",
                AsyncMock(return_value=None),
            ),
            patch(
                "apps.bot.handlers.defect.confirm.handler.register_defect",
                AsyncMock(),
            ) as register,
        ):
            await confirm_defect(make_callback(), ConfirmCB(confirmed=True), state, bot)

        register.assert_not_called()
        assert await state.get_state() is None

    async def test_verdict_is_not_recorded_without_an_employee(self, state, bot):
        from apps.bot.callback_data import VerdictCB
        from apps.bot.handlers.defect.verdict import receive_employee_verdict
        from apps.defects.constants import DefectVerdict

        await save_defect(state, DefectData(defect_id="1"))

        with (
            patch(
                "apps.bot.handlers.defect.verdict.get_employee",
                AsyncMock(return_value=None),
            ),
            patch("apps.bot.handlers.defect.verdict.services") as svc,
        ):
            await receive_employee_verdict(
                make_callback(),
                VerdictCB(value=DefectVerdict.DECOMMISSION),
                state,
                bot,
            )

        svc.save_employee_verdict.assert_not_called()
        assert await state.get_state() is None


class TestAfterPhotosStoresSerializableEmployees:
    """The roster is parked in state, so it must not hold live ORM objects."""

    def _orm_employee(self, pk=7, first="Ivan", last="Petrov"):
        emp = MagicMock()
        emp.id = pk
        emp.first_name = first
        emp.last_name = last
        return emp

    async def test_stores_employee_refs_not_model_instances(self, state):
        import json

        from apps.bot.handlers.defect.photo.routing import after_photos

        defect = DefectData(
            defect_type=DefectType.HUMAN_FACTOR, department="coupler_brake"
        )
        await save_defect(state, defect)

        with patch(
            "apps.bot.services.get_employees_by_department",
            AsyncMock(return_value=[self._orm_employee()]),
        ):
            await after_photos(AsyncMock(), defect, state)

        stored = (await state.get_data())[UD_RESP_EMPLOYEES]
        assert stored == [{"id": 7, "first_name": "Ivan", "last_name": "Petrov"}]
        assert json.dumps(stored)
        assert await state.get_state() == DefectSG.responsible_employee.state

    async def test_other_defect_types_go_to_the_measurement_step(self, state):
        from apps.bot.handlers.defect.photo.routing import after_photos

        defect = DefectData(defect_type=DefectType.WEAR)
        await save_defect(state, defect)

        await after_photos(AsyncMock(), defect, state)

        assert await state.get_state() == DefectSG.measurement_choice.state


class TestMeasurementChoice:
    async def test_add_starts_a_measurement_and_asks_for_the_dimension(self, state):
        from apps.bot.handlers.defect.measurement import measurement_add
        from apps.bot.user_data import MeasurementEntry

        await save_defect(state, DefectData())
        callback = make_callback()

        await measurement_add(callback, state)

        assert (await load_defect(state)).current_measurement == MeasurementEntry()
        assert await state.get_state() == DefectSG.measurement_dimension.state
        callback.answer.assert_awaited_once()

    async def test_done_moves_on_to_the_description(self, state):
        from apps.bot.handlers.defect.measurement import measurement_done

        await save_defect(state, DefectData())

        await measurement_done(make_callback(), state)

        assert await state.get_state() == DefectSG.desc.state

    async def test_done_does_not_need_a_form_in_state(self, state):
        from apps.bot.handlers.defect.measurement import measurement_done

        await measurement_done(make_callback(), state)

        assert await state.get_state() == DefectSG.desc.state
