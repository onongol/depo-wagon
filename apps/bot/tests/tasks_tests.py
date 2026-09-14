"""Tests for the open-defects flow.

Only the text formatter was covered before. The list is genuinely stateless —
every tap re-queries — so these exercise the handlers directly.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.bot.callback_data import StatusPickCB, StatusSetCB, TasksPageCB
from apps.bot.handlers.tasks import (
    my_tasks,
    my_tasks_page,
    set_defect_status,
    show_status_picker,
)
from apps.bot.messages import BotMessages as M
from apps.bot.tests.builders import make_callback, make_message
from apps.core.constants import EmployeeRole
from apps.defects.constants import DefectStatus

LIST = "apps.bot.handlers.tasks.list"
STATUS = "apps.bot.handlers.tasks.status"


def _make_defect(number="60123456"):
    defect = MagicMock()
    defect.id = uuid.uuid4()
    defect.wagon.number = number
    defect.get_node_display.return_value = "Wheelset"
    defect.get_defect_type_display.return_value = "Crack"
    defect.severity = "high"
    defect.status = DefectStatus.OPEN
    defect.inspector.short_name = "B. Bat"
    defect.inspected_at = None
    return defect


@pytest.fixture
def employee():
    emp = MagicMock()
    emp.id = 7
    emp.role = EmployeeRole.INSPECTOR
    return emp


def _services(defects, total=None):
    svc = MagicMock()
    count = len(defects) if total is None else total
    svc.get_open_defects = AsyncMock(return_value=defects)
    svc.get_open_defects_count = AsyncMock(return_value=count)
    svc.update_defect_status = AsyncMock(return_value=True)
    return svc


def _status_picks(kb):
    return [
        btn
        for row in kb.inline_keyboard
        for btn in row
        if btn.callback_data.startswith(StatusPickCB.__prefix__ + ":")
    ]


class TestMyTasks:
    async def test_refuses_an_unregistered_chat(self):
        message = make_message()

        with patch(f"{LIST}.get_employee", AsyncMock(return_value=None)):
            await my_tasks(message)

        message.answer.assert_awaited_once_with(
            str(M.NOT_REGISTERED), parse_mode=M.PARSE_MODE
        )

    async def test_says_so_when_there_is_nothing_open(self, employee):
        message = make_message()

        with (
            patch(f"{LIST}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", _services([])),
        ):
            await my_tasks(message)

        assert message.answer.await_args.args[0] == str(M.NO_TASKS)

    async def test_sends_a_new_message_with_a_keyboard(self, employee):
        message = make_message()

        with (
            patch(f"{LIST}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", _services([_make_defect()])),
        ):
            await my_tasks(message)

        assert message.answer.await_args.kwargs["reply_markup"] is not None

    @pytest.mark.parametrize(
        ("role", "offered"),
        [
            (EmployeeRole.INSPECTOR, True),
            (EmployeeRole.ENGINEER, True),
            (EmployeeRole.MANAGER, True),
            (EmployeeRole.MASTER, False),
            (EmployeeRole.WORKER, False),
        ],
    )
    async def test_offers_status_buttons_only_to_roles_that_may_use_them(
        self, employee, role, offered
    ):
        employee.role = role
        message = make_message()

        with (
            patch(f"{LIST}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", _services([_make_defect()])),
        ):
            await my_tasks(message)

        kb = message.answer.await_args.kwargs["reply_markup"]
        assert bool(_status_picks(kb)) is offered

    async def test_always_starts_at_the_first_page(self, employee):
        svc = _services([_make_defect()])

        with (
            patch(f"{LIST}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", svc),
        ):
            await my_tasks(make_message())

        assert svc.get_open_defects.await_args.kwargs["offset"] == 0

    @pytest.mark.parametrize("role", [*EmployeeRole.values, "unknown"])
    async def test_leaves_the_scope_to_the_query_whatever_the_role(
        self, employee, role
    ):
        employee.role = role
        svc = _services([])

        with (
            patch(f"{LIST}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", svc),
        ):
            await my_tasks(make_message())

        assert svc.get_open_defects.await_args.kwargs["employee"] is employee
        assert svc.get_open_defects_count.await_args.kwargs["employee"] is employee


class TestMyTasksPage:
    async def test_edits_in_place_rather_than_sending_a_new_message(self, employee):
        callback = make_callback()

        with (
            patch(f"{LIST}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", _services([_make_defect()])),
        ):
            await my_tasks_page(callback, TasksPageCB(page=1))

        callback.message.edit_text.assert_awaited_once()
        callback.message.answer.assert_not_called()

    async def test_answers_the_query(self, employee):
        callback = make_callback()

        with (
            patch(f"{LIST}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", _services([])),
        ):
            await my_tasks_page(callback, TasksPageCB(page=1))

        callback.answer.assert_awaited_once()

    async def test_offsets_the_query_by_the_requested_page(self, employee):
        svc = _services([_make_defect()], total=99)

        with (
            patch(f"{LIST}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", svc),
        ):
            await my_tasks_page(make_callback(), TasksPageCB(page=3))

        assert svc.get_open_defects.await_args.kwargs["offset"] == 3 * 5

    async def test_refuses_a_chat_that_lost_its_employee(self):
        """A stale keyboard outlives deactivation; it must not list anyone's defects."""
        svc = _services([_make_defect()])
        callback = make_callback()

        with (
            patch(f"{LIST}.get_employee", AsyncMock(return_value=None)),
            patch(f"{LIST}.services", svc),
        ):
            await my_tasks_page(callback, TasksPageCB(page=1))

        callback.message.edit_text.assert_awaited_once_with(
            str(M.NOT_REGISTERED), parse_mode=M.PARSE_MODE
        )
        svc.get_open_defects.assert_not_called()
        svc.get_open_defects_count.assert_not_called()


class TestShowStatusPicker:
    async def test_swaps_only_the_keyboard(self):
        callback = make_callback()
        defect_id = uuid.uuid4()

        await show_status_picker(callback, StatusPickCB(defect_id=defect_id, page=2))

        callback.message.edit_reply_markup.assert_awaited_once()
        callback.message.edit_text.assert_not_called()

    async def test_offers_every_status(self):
        callback = make_callback()

        await show_status_picker(callback, StatusPickCB(defect_id=uuid.uuid4(), page=0))

        kb = callback.message.edit_reply_markup.await_args.kwargs["reply_markup"]
        payloads = [b.callback_data for row in kb.inline_keyboard for b in row]
        statuses = {
            StatusSetCB.unpack(p).status
            for p in payloads
            if p.startswith(StatusSetCB.__prefix__ + ":")
        }
        assert statuses == set(DefectStatus.values)

    async def test_carries_the_page_into_the_status_buttons(self):
        callback = make_callback()

        await show_status_picker(callback, StatusPickCB(defect_id=uuid.uuid4(), page=4))

        kb = callback.message.edit_reply_markup.await_args.kwargs["reply_markup"]
        payloads = [b.callback_data for row in kb.inline_keyboard for b in row]
        pages = {
            StatusSetCB.unpack(p).page
            for p in payloads
            if p.startswith(StatusSetCB.__prefix__ + ":")
        }
        assert pages == {4}


class TestSetDefectStatus:
    async def test_refuses_a_chat_that_lost_its_employee(self):
        svc = _services([])
        list_svc = _services([_make_defect()])
        callback = make_callback()

        with (
            patch(f"{STATUS}.services", svc),
            patch(f"{STATUS}.get_employee", AsyncMock(return_value=None)),
            patch(f"{LIST}.services", list_svc),
        ):
            await set_defect_status(
                callback,
                StatusSetCB(defect_id=uuid.uuid4(), status=DefectStatus.CLOSED, page=0),
            )

        svc.update_defect_status.assert_not_called()
        list_svc.get_open_defects.assert_not_called()
        callback.message.edit_text.assert_awaited_once_with(
            str(M.NOT_REGISTERED), parse_mode=M.PARSE_MODE
        )

    @pytest.mark.parametrize("role", [*EmployeeRole.values, "unknown"])
    async def test_leaves_the_permission_check_to_the_query_whatever_the_role(
        self, employee, role
    ):
        employee.role = role
        svc = _services([])
        defect_id = uuid.uuid4()

        with (
            patch(f"{STATUS}.services", svc),
            patch(f"{STATUS}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", _services([])),
        ):
            await set_defect_status(
                make_callback(),
                StatusSetCB(defect_id=defect_id, status=DefectStatus.CLOSED, page=0),
            )

        svc.update_defect_status.assert_awaited_once_with(
            defect_id, DefectStatus.CLOSED, employee=employee
        )

    async def test_refreshes_the_list_at_the_same_page(self, employee):
        list_svc = _services([_make_defect()], total=99)
        callback = make_callback()

        with (
            patch(f"{STATUS}.services", _services([])),
            patch(f"{STATUS}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", list_svc),
        ):
            await set_defect_status(
                callback,
                StatusSetCB(
                    defect_id=uuid.uuid4(), status=DefectStatus.IN_PROGRESS, page=2
                ),
            )

        assert list_svc.get_open_defects.await_args.kwargs["offset"] == 2 * 5
        callback.message.edit_text.assert_awaited_once()

    async def test_reports_an_emptied_list(self, employee):
        callback = make_callback()

        with (
            patch(f"{STATUS}.services", _services([])),
            patch(f"{STATUS}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", _services([])),
        ):
            await set_defect_status(
                callback,
                StatusSetCB(defect_id=uuid.uuid4(), status=DefectStatus.CLOSED, page=0),
            )

        assert callback.message.edit_text.await_args.args[0] == str(M.NO_TASKS)

    @pytest.mark.parametrize(
        ("role", "offered"),
        [(EmployeeRole.INSPECTOR, True), (EmployeeRole.MASTER, False)],
    )
    async def test_warns_and_redraws_the_list_when_refused(
        self, employee, role, offered
    ):
        employee.role = role
        svc = _services([])
        svc.update_defect_status = AsyncMock(return_value=False)
        callback = make_callback()

        with (
            patch(f"{STATUS}.services", svc),
            patch(f"{STATUS}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", _services([_make_defect()])),
        ):
            await set_defect_status(
                callback,
                StatusSetCB(defect_id=uuid.uuid4(), status=DefectStatus.CLOSED, page=0),
            )

        assert callback.message.answer.await_args.args[0] == str(
            M.STATUS_CHANGE_REFUSED
        )
        kb = callback.message.edit_text.await_args.kwargs["reply_markup"]
        assert bool(_status_picks(kb)) is offered

    async def test_reports_a_failed_save_and_leaves_the_list_alone(self, employee):
        svc = _services([])
        svc.update_defect_status = AsyncMock(side_effect=RuntimeError("db is down"))
        callback = make_callback()

        with (
            patch(f"{STATUS}.services", svc),
            patch(f"{STATUS}.get_employee", AsyncMock(return_value=employee)),
            patch(f"{LIST}.services", _services([_make_defect()])),
        ):
            await set_defect_status(
                callback,
                StatusSetCB(defect_id=uuid.uuid4(), status=DefectStatus.CLOSED, page=0),
            )

        assert callback.message.answer.await_args.args[0] == str(M.STATUS_CHANGE_FAILED)
        callback.message.edit_text.assert_not_awaited()
