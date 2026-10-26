"""Tests for the open-defects list, the defect card and the status change.

Every screen is stateless — each tap re-queries — so these exercise the
handlers directly with the services mocked.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.bot.callback_data import (
    DefectCardCB,
    DefectOpenCB,
    StatusAskCB,
    StatusPickCB,
    StatusSetCB,
    TasksPageCB,
)
from apps.bot.handlers.tasks import (
    ask_status_confirmation,
    my_tasks,
    my_tasks_page,
    open_defect_card,
    set_defect_status,
    show_defect_card,
    show_status_picker,
)
from apps.bot.handlers.tasks.router import get_tasks_router
from apps.bot.handlers.tasks.text import (
    build_card_text,
    build_defect_unavailable_toast,
    build_no_tasks_text,
    build_status_changed_toast,
    build_status_confirm_text,
    build_status_failed_toast,
    build_status_pick_text,
    build_status_refused_toast,
)
from apps.bot.services.defect_card import DefectCard
from apps.bot.tests.builders import (
    CHAT_ID,
    MESSAGE_ID,
    USER_ID,
    make_callback,
    make_message,
    unpacked,
)
from apps.core.constants import EmployeeRole
from apps.defects.constants import DefectStatus

RENDER = "apps.bot.handlers.tasks.render"
CARD = "apps.bot.handlers.tasks.card"
STATUS = "apps.bot.handlers.tasks.status"

BOTH_TARGETS = (DefectStatus.IN_PROGRESS, DefectStatus.CLOSED)


def _make_defect(number="60123456", status=DefectStatus.OPEN):
    defect = MagicMock()
    defect.id = defect.pk = uuid.uuid4()
    defect.wagon.number = number
    defect.status = status
    defect.severity = "high"
    defect.get_node_display.return_value = "Wheelset"
    defect.get_defect_type_display.return_value = "Crack"
    defect.get_severity_display.return_value = "High"
    defect.get_department_display.return_value = "Repair-1"
    defect.part_number = ""
    defect.inspector.short_name = "B. Bat"
    defect.inspector.full_name = "Bat Erdene"
    defect.responsible_employee = None
    defect.inspected_at = None
    defect.description = ""
    defect.ai_defect_class = ""
    defect.verdict = ""
    return defect


def _card(defect=None, targets=BOTH_TARGETS):
    return DefectCard(
        defect=defect or _make_defect(),
        measurements=(),
        photo_count=0,
        targets=targets,
    )


@pytest.fixture
def employee():
    emp = MagicMock()
    emp.id = 7
    emp.role = EmployeeRole.INSPECTOR
    return emp


@pytest.fixture
def svc():
    mock = MagicMock()
    mock.get_open_defects = AsyncMock(return_value=[_make_defect()])
    mock.get_open_defects_count = AsyncMock(return_value=1)
    mock.get_defect_card = AsyncMock(return_value=_card())
    mock.update_defect_status = AsyncMock(return_value=_card())

    with (
        patch(f"{RENDER}.services", mock),
        patch(f"{CARD}.services", mock),
        patch(f"{STATUS}.services", mock),
    ):
        yield mock


def _edit(callback):
    """(text, entities) and keyboard of the one edit the handler made, by id."""
    callback.bot.edit_message_text.assert_awaited_once()
    call = callback.bot.edit_message_text.await_args.kwargs
    assert (call["chat_id"], call["message_id"]) == (CHAT_ID, MESSAGE_ID)
    return (call["text"], call["entities"]), call["reply_markup"]


def _alerted(callback, text) -> None:
    callback.answer.assert_awaited_once_with(str(text), show_alert=True)


def _answered_quietly(callback) -> None:
    callback.answer.assert_awaited_once_with()


def test_every_handler_is_for_a_registered_chat_only():
    """A stale keyboard outlives deactivation; it must not list anyone's defects."""
    router = get_tasks_router()
    handlers = [*router.message.handlers, *router.callback_query.handlers]

    assert handlers
    assert all(handler.flags.get("registered") for handler in handlers)


class TestMyTasks:
    async def test_says_so_when_there_is_nothing_open(self, svc, employee, state):
        svc.get_open_defects.return_value = []
        svc.get_open_defects_count.return_value = 0
        message = make_message()

        await my_tasks(message, state, employee)

        message.answer.assert_awaited_once_with(**build_no_tasks_text().as_kwargs())

    async def test_sends_a_new_message_with_a_keyboard(self, svc, employee, state):
        message = make_message()

        await my_tasks(message, state, employee)

        assert message.answer.await_args.kwargs["reply_markup"] is not None

    @pytest.mark.parametrize("role", EmployeeRole.values)
    async def test_every_role_can_open_the_cards(self, svc, employee, role, state):
        employee.role = role
        message = make_message()

        await my_tasks(message, state, employee)

        kb = message.answer.await_args.kwargs["reply_markup"]
        assert unpacked(kb, DefectCardCB)
        assert unpacked(kb, StatusPickCB) == []

    async def test_always_starts_at_the_first_page(self, svc, employee, state):
        await my_tasks(make_message(), state, employee)

        assert svc.get_open_defects.await_args.kwargs["offset"] == 0

    @pytest.mark.parametrize("role", [*EmployeeRole.values, "unknown"])
    async def test_leaves_the_scope_to_the_query_whatever_the_role(
        self, svc, employee, role, state
    ):
        employee.role = role

        await my_tasks(make_message(), state, employee)

        assert svc.get_open_defects.await_args.kwargs["employee"] is employee
        assert svc.get_open_defects_count.await_args.kwargs["employee"] is employee


class TestMyTasksPage:
    async def test_edits_in_place_rather_than_sending_a_new_message(
        self, svc, employee
    ):
        callback = make_callback()

        await my_tasks_page(callback, TasksPageCB(page=1), employee)

        callback.bot.edit_message_text.assert_awaited_once()
        callback.message.answer.assert_not_called()

    async def test_answers_the_query(self, svc, employee):
        callback = make_callback()

        await my_tasks_page(callback, TasksPageCB(page=1), employee)

        _answered_quietly(callback)

    async def test_offsets_the_query_by_the_requested_page(self, svc, employee):
        svc.get_open_defects_count.return_value = 99

        await my_tasks_page(make_callback(), TasksPageCB(page=3), employee)

        assert svc.get_open_defects.await_args.kwargs["offset"] == 3 * 5

    async def test_a_page_emptied_since_shows_the_last_one_left(self, svc, employee):
        """Closing the last defect on a page must not read as "no open defects"."""
        svc.get_open_defects_count.return_value = 6

        await my_tasks_page(make_callback(), TasksPageCB(page=4), employee)

        assert svc.get_open_defects.await_args.kwargs["offset"] == 5


class TestShowDefectCard:
    async def test_looks_the_defect_up_for_this_employee(self, svc, employee):
        defect_id = uuid.uuid4()

        await show_defect_card(
            make_callback(), DefectCardCB(defect_id=defect_id, page=0), employee
        )

        svc.get_defect_card.assert_awaited_once_with(defect_id, employee=employee)

    async def test_replaces_the_list_with_the_card(self, svc, employee):
        card = _card()
        svc.get_defect_card.return_value = card
        callback = make_callback()

        await show_defect_card(
            callback, DefectCardCB(defect_id=card.defect.pk, page=2), employee
        )

        text, kb = _edit(callback)
        assert text == build_card_text(card).render()
        assert [cb.page for cb in unpacked(kb, TasksPageCB)] == [2]
        _answered_quietly(callback)

    async def test_goes_out_as_entities_not_html(self, svc, employee):
        callback = make_callback()

        await show_defect_card(
            callback, DefectCardCB(defect_id=uuid.uuid4(), page=0), employee
        )

        assert callback.bot.edit_message_text.await_args.kwargs["parse_mode"] is None

    @pytest.mark.parametrize(
        ("targets", "offered"), [(BOTH_TARGETS, True), ((), False)]
    )
    async def test_offers_the_status_change_only_when_there_is_one(
        self, svc, employee, targets, offered
    ):
        svc.get_defect_card.return_value = _card(targets=targets)
        callback = make_callback()

        await show_defect_card(
            callback, DefectCardCB(defect_id=uuid.uuid4(), page=0), employee
        )

        _, kb = _edit(callback)
        assert bool(unpacked(kb, StatusPickCB)) is offered

    async def test_an_unavailable_defect_alerts_and_returns_to_the_list(
        self, svc, employee
    ):
        svc.get_defect_card.return_value = None
        callback = make_callback()

        await show_defect_card(
            callback, DefectCardCB(defect_id=uuid.uuid4(), page=0), employee
        )

        _alerted(callback, build_defect_unavailable_toast())
        _, kb = _edit(callback)
        assert unpacked(kb, DefectCardCB)


class TestOpenDefectCard:
    """From a notification: the card comes under it, and the notification stays."""

    async def test_looks_the_defect_up_for_this_employee(self, svc, employee):
        defect_id = uuid.uuid4()

        await open_defect_card(
            make_callback(), DefectOpenCB(defect_id=defect_id), employee
        )

        svc.get_defect_card.assert_awaited_once_with(defect_id, employee=employee)

    async def test_sends_the_card_as_a_new_message(self, svc, employee):
        card = _card()
        svc.get_defect_card.return_value = card
        callback = make_callback()

        await open_defect_card(
            callback, DefectOpenCB(defect_id=card.defect.pk), employee
        )

        _answered_quietly(callback)
        callback.bot.edit_message_text.assert_not_awaited()
        sent = callback.bot.send_message.await_args
        assert sent.args == (USER_ID,)
        assert (sent.kwargs["text"], sent.kwargs["entities"]) == (
            build_card_text(card).render()
        )
        kb = sent.kwargs["reply_markup"]
        assert unpacked(kb, StatusPickCB)
        assert [cb.page for cb in unpacked(kb, TasksPageCB)] == [0]

    async def test_an_unavailable_defect_alerts_and_sends_nothing(self, svc, employee):
        svc.get_defect_card.return_value = None
        callback = make_callback()

        await open_defect_card(callback, DefectOpenCB(defect_id=uuid.uuid4()), employee)

        _alerted(callback, build_defect_unavailable_toast())
        callback.bot.send_message.assert_not_awaited()
        callback.bot.edit_message_text.assert_not_awaited()
        svc.get_open_defects.assert_not_called()


class TestShowStatusPicker:
    async def test_offers_only_the_statuses_the_card_allows(self, svc, employee):
        card = _card(targets=(DefectStatus.CLOSED,))
        svc.get_defect_card.return_value = card
        callback = make_callback()

        await show_status_picker(
            callback, StatusPickCB(defect_id=card.defect.pk, page=4), employee
        )

        text, kb = _edit(callback)
        assert text == build_status_pick_text(card).render()
        asks = unpacked(kb, StatusAskCB)
        assert [(cb.status, cb.page) for cb in asks] == [(DefectStatus.CLOSED, 4)]
        _answered_quietly(callback)

    async def test_nothing_to_change_alerts_and_shows_the_card(self, svc, employee):
        card = _card(defect=_make_defect(status=DefectStatus.CLOSED), targets=())
        svc.get_defect_card.return_value = card
        callback = make_callback()

        await show_status_picker(
            callback, StatusPickCB(defect_id=card.defect.pk, page=0), employee
        )

        _alerted(callback, build_status_refused_toast())
        text, kb = _edit(callback)
        assert text == build_card_text(card).render()
        assert unpacked(kb, StatusAskCB) == []

    async def test_an_unavailable_defect_alerts_and_returns_to_the_list(
        self, svc, employee
    ):
        svc.get_defect_card.return_value = None
        callback = make_callback()

        await show_status_picker(
            callback, StatusPickCB(defect_id=uuid.uuid4(), page=0), employee
        )

        _alerted(callback, build_defect_unavailable_toast())
        _, kb = _edit(callback)
        assert unpacked(kb, DefectCardCB)


class TestAskStatusConfirmation:
    async def test_asks_before_saving(self, svc, employee):
        card = _card()
        svc.get_defect_card.return_value = card
        callback = make_callback()

        await ask_status_confirmation(
            callback,
            StatusAskCB(defect_id=card.defect.pk, status=DefectStatus.CLOSED, page=1),
            employee,
        )

        text, kb = _edit(callback)
        assert (
            text == build_status_confirm_text(card.defect, DefectStatus.CLOSED).render()
        )
        [save] = unpacked(kb, StatusSetCB)
        assert (save.status, save.page) == (DefectStatus.CLOSED, 1)
        svc.update_defect_status.assert_not_called()
        _answered_quietly(callback)

    async def test_a_status_no_longer_allowed_alerts_and_shows_the_card(
        self, svc, employee
    ):
        card = _card(targets=(DefectStatus.OPEN, DefectStatus.CLOSED))
        svc.get_defect_card.return_value = card
        callback = make_callback()

        await ask_status_confirmation(
            callback,
            StatusAskCB(
                defect_id=card.defect.pk, status=DefectStatus.IN_PROGRESS, page=0
            ),
            employee,
        )

        _alerted(callback, build_status_refused_toast())
        text, kb = _edit(callback)
        assert text == build_card_text(card).render()
        assert unpacked(kb, StatusSetCB) == []

    async def test_an_unavailable_defect_alerts_and_returns_to_the_list(
        self, svc, employee
    ):
        svc.get_defect_card.return_value = None
        callback = make_callback()

        await ask_status_confirmation(
            callback,
            StatusAskCB(defect_id=uuid.uuid4(), status=DefectStatus.CLOSED, page=0),
            employee,
        )

        _alerted(callback, build_defect_unavailable_toast())


class TestSetDefectStatus:
    @pytest.mark.parametrize("role", [*EmployeeRole.values, "unknown"])
    async def test_leaves_the_permission_check_to_the_query_whatever_the_role(
        self, svc, employee, role
    ):
        employee.role = role
        defect_id = uuid.uuid4()

        await set_defect_status(
            make_callback(),
            StatusSetCB(defect_id=defect_id, status=DefectStatus.CLOSED, page=0),
            employee,
        )

        svc.update_defect_status.assert_awaited_once_with(
            defect_id, DefectStatus.CLOSED, employee=employee
        )

    async def test_a_saved_status_is_confirmed_quietly_on_the_card(self, svc, employee):
        card = _card(defect=_make_defect(status=DefectStatus.IN_PROGRESS))
        svc.update_defect_status.return_value = card
        callback = make_callback()

        await set_defect_status(
            callback,
            StatusSetCB(
                defect_id=card.defect.pk, status=DefectStatus.IN_PROGRESS, page=2
            ),
            employee,
        )

        callback.answer.assert_awaited_once_with(
            build_status_changed_toast(DefectStatus.IN_PROGRESS)
        )
        text, kb = _edit(callback)
        assert text == build_card_text(card).render()
        assert [cb.page for cb in unpacked(kb, TasksPageCB)] == [2]
        svc.get_defect_card.assert_not_called()

    async def test_a_refusal_alerts_and_redraws_the_card(self, svc, employee):
        svc.update_defect_status.return_value = None
        card = _card(defect=_make_defect(status=DefectStatus.CLOSED), targets=())
        svc.get_defect_card.return_value = card
        callback = make_callback()

        await set_defect_status(
            callback,
            StatusSetCB(defect_id=card.defect.pk, status=DefectStatus.OPEN, page=0),
            employee,
        )

        _alerted(callback, build_status_refused_toast())
        text, kb = _edit(callback)
        assert text == build_card_text(card).render()
        assert unpacked(kb, StatusPickCB) == []

    async def test_a_defect_gone_from_view_returns_to_the_list(self, svc, employee):
        svc.update_defect_status.return_value = None
        svc.get_defect_card.return_value = None
        svc.get_open_defects_count.return_value = 99
        callback = make_callback()

        await set_defect_status(
            callback,
            StatusSetCB(defect_id=uuid.uuid4(), status=DefectStatus.CLOSED, page=2),
            employee,
        )

        assert svc.get_open_defects.await_args.kwargs["offset"] == 2 * 5
        _, kb = _edit(callback)
        assert unpacked(kb, DefectCardCB)

    async def test_reports_a_failed_save_and_leaves_the_message_alone(
        self, svc, employee
    ):
        svc.update_defect_status.side_effect = RuntimeError("db is down")
        callback = make_callback()

        await set_defect_status(
            callback,
            StatusSetCB(defect_id=uuid.uuid4(), status=DefectStatus.CLOSED, page=0),
            employee,
        )

        _alerted(callback, build_status_failed_toast())
        callback.bot.edit_message_text.assert_not_awaited()
