"""The open-defects queries, run against the database."""

import pytest
from asgiref.sync import sync_to_async
from model_bakery import baker

from apps.bot.services.open_defects import get_open_defects, get_open_defects_count
from apps.core.constants import EmployeeRole
from apps.defects.constants import DefectStatus

make = sync_to_async(baker.make)

SCOPED_ROLES = [EmployeeRole.INSPECTOR, EmployeeRole.MASTER, EmployeeRole.WORKER]
ALL_ROLES = [EmployeeRole.ENGINEER, EmployeeRole.MANAGER]


async def _defect(**fields):
    wagon = await make("core.Wagon", manufacture_year=2000)
    defaults = {"wagon": wagon, "status": DefectStatus.OPEN}
    return await make("defects.Defect", **(defaults | fields))


async def _employee(role=EmployeeRole.INSPECTOR, **fields):
    return await make("core.Employee", role=role, **fields)


@pytest.mark.django_db(transaction=True)
class TestOpenDefects:
    @pytest.mark.parametrize("role", SCOPED_ROLES)
    async def test_lists_only_their_own_defects(self, role):
        mine = await _employee(role)
        own = await _defect(inspector=mine)
        await _defect(inspector=await _employee())
        await _defect(inspector=None)

        defects = await get_open_defects(employee_id=mine.pk)

        assert [d.pk for d in defects] == [own.pk]
        assert await get_open_defects_count(employee_id=mine.pk) == 1

    @pytest.mark.parametrize("role", ALL_ROLES)
    async def test_engineers_and_managers_list_every_open_defect(self, role):
        employee = await _employee(role)
        await _defect(inspector=await _employee())
        await _defect(inspector=await _employee())
        await _defect(inspector=None, status=DefectStatus.IN_PROGRESS)
        await _defect(status=DefectStatus.CLOSED)

        assert len(await get_open_defects(employee_id=employee.pk, limit=10)) == 3
        assert await get_open_defects_count(employee_id=employee.pk) == 3

    async def test_skips_closed_defects(self):
        mine = await _employee()
        await _defect(inspector=mine, status=DefectStatus.IN_PROGRESS)
        await _defect(inspector=mine, status=DefectStatus.CLOSED)

        assert await get_open_defects_count(employee_id=mine.pk) == 1

    async def test_an_inactive_employee_sees_nothing(self):
        engineer = await _employee(EmployeeRole.ENGINEER, is_active=False)
        await _defect(inspector=engineer)
        await _defect(inspector=None)

        assert await get_open_defects(employee_id=engineer.pk) == []
        assert await get_open_defects_count(employee_id=engineer.pk) == 0

    async def test_an_unknown_employee_sees_nothing(self):
        await _defect(inspector=None)

        assert await get_open_defects(employee_id=999_999) == []
        assert await get_open_defects_count(employee_id=999_999) == 0

    async def test_a_missing_employee_is_refused_rather_than_widened(self):
        await _defect(inspector=None)
        await _defect(inspector=await _employee())

        with pytest.raises(ValueError, match="employee_id"):
            await get_open_defects(employee_id=None)
        with pytest.raises(ValueError, match="employee_id"):
            await get_open_defects_count(employee_id=None)

    async def test_the_employee_cannot_be_left_out(self):
        with pytest.raises(TypeError):
            await get_open_defects()
        with pytest.raises(TypeError):
            await get_open_defects_count()
