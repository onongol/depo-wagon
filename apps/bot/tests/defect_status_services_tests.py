"""The status update, run against the database."""

import uuid
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from model_bakery import baker

from apps.bot.constants import STATUS_TRANSITIONS
from apps.bot.services.defect import update_defect_status
from apps.core.constants import EmployeeRole
from apps.defects.constants import DefectStatus

make = sync_to_async(baker.make)

ALL_ROLES = [EmployeeRole.ENGINEER, EmployeeRole.MANAGER]
REFUSED_ROLES = [EmployeeRole.MASTER, EmployeeRole.WORKER]


async def _defect(**fields):
    wagon = await make("core.Wagon", manufacture_year=2000)
    defaults = {"wagon": wagon, "status": DefectStatus.OPEN}
    return await make("defects.Defect", **(defaults | fields))


async def _employee(role=EmployeeRole.INSPECTOR, **fields):
    return await make("core.Employee", role=role, **fields)


async def _status(defect):
    await sync_to_async(defect.refresh_from_db)()
    return defect.status


@pytest.mark.django_db(transaction=True)
class TestInspectors:
    async def test_save_the_status_on_their_own_defect(self):
        mine = await _employee()
        defect = await _defect(inspector=mine)

        card = await update_defect_status(
            defect.pk, DefectStatus.IN_PROGRESS, employee=mine
        )

        assert card is not None
        assert await _status(defect) == DefectStatus.IN_PROGRESS

    async def test_closing_stamps_repaired_at(self):
        mine = await _employee()
        defect = await _defect(inspector=mine)

        await update_defect_status(defect.pk, DefectStatus.CLOSED, employee=mine)

        await sync_to_async(defect.refresh_from_db)()
        assert defect.repaired_at is not None

    async def test_leave_another_employees_defect_alone(self):
        mine = await _employee()
        defect = await _defect(inspector=await _employee())

        card = await update_defect_status(defect.pk, DefectStatus.CLOSED, employee=mine)

        assert card is None
        assert await _status(defect) == DefectStatus.OPEN

    async def test_leave_a_defect_with_no_inspector_alone(self):
        mine = await _employee()
        defect = await _defect(inspector=None)

        card = await update_defect_status(defect.pk, DefectStatus.CLOSED, employee=mine)

        assert card is None
        assert await _status(defect) == DefectStatus.OPEN


@pytest.mark.django_db(transaction=True)
class TestEngineersAndManagers:
    @pytest.mark.parametrize("role", ALL_ROLES)
    async def test_save_the_status_on_anyones_defect(self, role):
        employee = await _employee(role)
        defect = await _defect(inspector=await _employee())

        card = await update_defect_status(
            defect.pk, DefectStatus.CLOSED, employee=employee
        )

        assert card is not None
        assert await _status(defect) == DefectStatus.CLOSED

    @pytest.mark.parametrize("role", ALL_ROLES)
    async def test_save_the_status_on_a_defect_with_no_inspector(self, role):
        employee = await _employee(role)
        defect = await _defect(inspector=None)

        assert (
            await update_defect_status(
                defect.pk, DefectStatus.CLOSED, employee=employee
            )
            is not None
        )

    @pytest.mark.parametrize("role", ALL_ROLES)
    async def test_a_missing_defect_is_reported(self, role):
        employee = await _employee(role)

        assert (
            await update_defect_status(
                uuid.uuid4(), DefectStatus.CLOSED, employee=employee
            )
            is None
        )


@pytest.mark.django_db(transaction=True)
class TestRefused:
    @pytest.mark.parametrize("role", REFUSED_ROLES)
    async def test_other_roles_leave_even_their_own_defect_alone(self, role):
        employee = await _employee(role)
        defect = await _defect(inspector=employee)

        card = await update_defect_status(
            defect.pk, DefectStatus.CLOSED, employee=employee
        )

        assert card is None
        assert await _status(defect) == DefectStatus.OPEN

    async def test_a_missing_employee_is_refused_rather_than_widened(self):
        defect = await _defect(inspector=None)

        with pytest.raises(ValueError, match="employee"):
            await update_defect_status(defect.pk, DefectStatus.CLOSED, employee=None)

        assert await _status(defect) == DefectStatus.OPEN

    async def test_the_employee_cannot_be_left_out(self):
        with pytest.raises(TypeError):
            await update_defect_status(uuid.uuid4(), DefectStatus.CLOSED)


@pytest.mark.django_db(transaction=True)
class TestTransitions:
    @pytest.mark.parametrize("target", DefectStatus.values)
    async def test_a_closed_defect_stays_closed(self, target):
        engineer = await _employee(EmployeeRole.ENGINEER)
        defect = await _defect(status=DefectStatus.CLOSED)

        card = await update_defect_status(defect.pk, target, employee=engineer)

        assert card is None
        assert await _status(defect) == DefectStatus.CLOSED

    async def test_work_can_be_handed_back(self):
        mine = await _employee()
        defect = await _defect(inspector=mine, status=DefectStatus.IN_PROGRESS)

        card = await update_defect_status(defect.pk, DefectStatus.OPEN, employee=mine)

        assert card is not None
        assert await _status(defect) == DefectStatus.OPEN

    async def test_the_current_status_is_not_a_change(self):
        mine = await _employee()
        defect = await _defect(inspector=mine)

        card = await update_defect_status(defect.pk, DefectStatus.OPEN, employee=mine)

        assert card is None

    async def test_the_saved_card_comes_back_fresh(self):
        """The card is read inside the write transaction, so it shows the new state."""
        mine = await _employee()
        defect = await _defect(inspector=mine)

        card = await update_defect_status(
            defect.pk, DefectStatus.IN_PROGRESS, employee=mine
        )

        assert card.defect.status == DefectStatus.IN_PROGRESS
        assert card.targets == STATUS_TRANSITIONS[DefectStatus.IN_PROGRESS]

    async def test_the_change_is_recorded_in_the_history(self):
        mine = await _employee()
        defect = await _defect(inspector=mine)
        before = await sync_to_async(defect.history.count)()

        await update_defect_status(defect.pk, DefectStatus.IN_PROGRESS, employee=mine)

        assert await sync_to_async(defect.history.count)() == before + 1

    async def test_closing_queues_the_embedding_once_committed(self):
        mine = await _employee()
        defect = await _defect(inspector=mine)

        with patch("apps.ai_service.tasks.embed_defect_task.delay") as delay:
            await update_defect_status(defect.pk, DefectStatus.CLOSED, employee=mine)

        delay.assert_called_once_with(str(defect.pk))
