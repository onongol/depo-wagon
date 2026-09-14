"""The status update, run against the database."""

import uuid

import pytest
from asgiref.sync import sync_to_async
from model_bakery import baker

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

        saved = await update_defect_status(
            defect.pk, DefectStatus.IN_PROGRESS, employee_id=mine.pk
        )

        assert saved is True
        assert await _status(defect) == DefectStatus.IN_PROGRESS

    async def test_closing_stamps_repaired_at(self):
        mine = await _employee()
        defect = await _defect(inspector=mine)

        await update_defect_status(defect.pk, DefectStatus.CLOSED, employee_id=mine.pk)

        await sync_to_async(defect.refresh_from_db)()
        assert defect.repaired_at is not None

    async def test_leave_another_employees_defect_alone(self):
        mine = await _employee()
        defect = await _defect(inspector=await _employee())

        saved = await update_defect_status(
            defect.pk, DefectStatus.CLOSED, employee_id=mine.pk
        )

        assert saved is False
        assert await _status(defect) == DefectStatus.OPEN

    async def test_leave_a_defect_with_no_inspector_alone(self):
        mine = await _employee()
        defect = await _defect(inspector=None)

        saved = await update_defect_status(
            defect.pk, DefectStatus.CLOSED, employee_id=mine.pk
        )

        assert saved is False
        assert await _status(defect) == DefectStatus.OPEN


@pytest.mark.django_db(transaction=True)
class TestEngineersAndManagers:
    @pytest.mark.parametrize("role", ALL_ROLES)
    async def test_save_the_status_on_anyones_defect(self, role):
        employee = await _employee(role)
        defect = await _defect(inspector=await _employee())

        saved = await update_defect_status(
            defect.pk, DefectStatus.CLOSED, employee_id=employee.pk
        )

        assert saved is True
        assert await _status(defect) == DefectStatus.CLOSED

    @pytest.mark.parametrize("role", ALL_ROLES)
    async def test_save_the_status_on_a_defect_with_no_inspector(self, role):
        employee = await _employee(role)
        defect = await _defect(inspector=None)

        assert (
            await update_defect_status(
                defect.pk, DefectStatus.CLOSED, employee_id=employee.pk
            )
            is True
        )

    @pytest.mark.parametrize("role", ALL_ROLES)
    async def test_a_missing_defect_is_reported(self, role):
        employee = await _employee(role)

        assert (
            await update_defect_status(
                uuid.uuid4(), DefectStatus.CLOSED, employee_id=employee.pk
            )
            is False
        )


@pytest.mark.django_db(transaction=True)
class TestRefused:
    @pytest.mark.parametrize("role", REFUSED_ROLES)
    async def test_other_roles_leave_even_their_own_defect_alone(self, role):
        employee = await _employee(role)
        defect = await _defect(inspector=employee)

        saved = await update_defect_status(
            defect.pk, DefectStatus.CLOSED, employee_id=employee.pk
        )

        assert saved is False
        assert await _status(defect) == DefectStatus.OPEN

    async def test_an_inactive_employee_is_refused(self):
        engineer = await _employee(EmployeeRole.ENGINEER, is_active=False)
        defect = await _defect(inspector=None)

        saved = await update_defect_status(
            defect.pk, DefectStatus.CLOSED, employee_id=engineer.pk
        )

        assert saved is False
        assert await _status(defect) == DefectStatus.OPEN

    async def test_an_unknown_employee_is_refused(self):
        defect = await _defect(inspector=None)

        saved = await update_defect_status(
            defect.pk, DefectStatus.CLOSED, employee_id=999_999
        )

        assert saved is False
        assert await _status(defect) == DefectStatus.OPEN

    async def test_a_missing_employee_is_refused_rather_than_widened(self):
        defect = await _defect(inspector=None)

        with pytest.raises(ValueError, match="employee_id"):
            await update_defect_status(defect.pk, DefectStatus.CLOSED, employee_id=None)

        assert await _status(defect) == DefectStatus.OPEN

    async def test_the_employee_cannot_be_left_out(self):
        with pytest.raises(TypeError):
            await update_defect_status(uuid.uuid4(), DefectStatus.CLOSED)
