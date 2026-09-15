"""The open-defects queries, run against the database."""

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from django.utils import timezone
from model_bakery import baker

from apps.bot.handlers.tasks.text import build_text
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

        defects = await get_open_defects(employee=mine)

        assert [d.pk for d in defects] == [own.pk]
        assert await get_open_defects_count(employee=mine) == 1

    @pytest.mark.parametrize("role", ALL_ROLES)
    async def test_engineers_and_managers_list_every_open_defect(self, role):
        employee = await _employee(role)
        await _defect(inspector=await _employee())
        await _defect(inspector=await _employee())
        await _defect(inspector=None, status=DefectStatus.IN_PROGRESS)
        await _defect(status=DefectStatus.CLOSED)

        assert len(await get_open_defects(employee=employee, limit=10)) == 3
        assert await get_open_defects_count(employee=employee) == 3

    async def test_skips_closed_defects(self):
        mine = await _employee()
        await _defect(inspector=mine, status=DefectStatus.IN_PROGRESS)
        await _defect(inspector=mine, status=DefectStatus.CLOSED)

        assert await get_open_defects_count(employee=mine) == 1

    async def test_pages_through_a_shared_inspection_time_in_a_fixed_order(self):
        mine = await _employee()
        inspected_at = timezone.now()
        created = [
            await _defect(inspector=mine, inspected_at=inspected_at) for _ in range(5)
        ]

        pages = [
            await get_open_defects(employee=mine, limit=2, offset=offset)
            for offset in (0, 2, 4)
        ]

        paged = [d.pk for page in pages for d in page]
        assert paged == sorted((d.pk for d in created), reverse=True)

    async def test_a_missing_employee_is_refused_rather_than_widened(self):
        await _defect(inspector=None)
        await _defect(inspector=await _employee())

        with pytest.raises(ValueError, match="employee"):
            await get_open_defects(employee=None)
        with pytest.raises(ValueError, match="employee"):
            await get_open_defects_count(employee=None)

    async def test_the_employee_cannot_be_left_out(self):
        with pytest.raises(TypeError):
            await get_open_defects()
        with pytest.raises(TypeError):
            await get_open_defects_count()


@pytest.mark.django_db
def test_the_list_text_reads_nothing_the_page_did_not_load(django_assert_num_queries):
    employee = baker.make("core.Employee", role=EmployeeRole.ENGINEER)
    for inspector in [baker.make("core.Employee"), baker.make("core.Employee"), None]:
        wagon = baker.make("core.Wagon", manufacture_year=2000)
        baker.make(
            "defects.Defect", wagon=wagon, inspector=inspector, status=DefectStatus.OPEN
        )
    defects = async_to_sync(get_open_defects)(employee=employee)

    with django_assert_num_queries(0):
        build_text(defects, page=0, total=len(defects))
