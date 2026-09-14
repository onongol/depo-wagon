"""The open-defects queries, run against the database."""

import pytest
from asgiref.sync import sync_to_async
from model_bakery import baker

from apps.bot.services.open_defects import (
    get_all_open_defects,
    get_all_open_defects_count,
    get_open_defects,
    get_open_defects_count,
)
from apps.defects.constants import DefectStatus

make = sync_to_async(baker.make)


async def _defect(**fields):
    wagon = await make("core.Wagon", manufacture_year=2000)
    defaults = {"wagon": wagon, "status": DefectStatus.OPEN}
    return await make("defects.Defect", **(defaults | fields))


@pytest.mark.django_db(transaction=True)
class TestOwnOpenDefects:
    async def test_lists_only_that_inspectors_defects(self):
        mine = await make("core.Employee")
        other = await make("core.Employee")
        own = await _defect(inspector=mine)
        await _defect(inspector=other)
        await _defect(inspector=None)

        defects = await get_open_defects(employee_id=mine.pk)

        assert [d.pk for d in defects] == [own.pk]
        assert await get_open_defects_count(employee_id=mine.pk) == 1

    async def test_skips_closed_defects(self):
        mine = await make("core.Employee")
        await _defect(inspector=mine, status=DefectStatus.IN_PROGRESS)
        await _defect(inspector=mine, status=DefectStatus.CLOSED)

        assert await get_open_defects_count(employee_id=mine.pk) == 1

    async def test_a_missing_employee_is_refused_rather_than_widened(self):
        await _defect(inspector=None)
        await _defect(inspector=await make("core.Employee"))

        with pytest.raises(ValueError, match="employee_id"):
            await get_open_defects(employee_id=None)
        with pytest.raises(ValueError, match="employee_id"):
            await get_open_defects_count(employee_id=None)

    async def test_the_employee_cannot_be_left_out(self):
        with pytest.raises(TypeError):
            await get_open_defects()
        with pytest.raises(TypeError):
            await get_open_defects_count()


@pytest.mark.django_db(transaction=True)
class TestAllOpenDefects:
    async def test_lists_every_inspectors_open_defects(self):
        await _defect(inspector=await make("core.Employee"))
        await _defect(inspector=await make("core.Employee"))
        await _defect(inspector=None, status=DefectStatus.IN_PROGRESS)
        await _defect(status=DefectStatus.CLOSED)

        assert len(await get_all_open_defects(limit=10)) == 3
        assert await get_all_open_defects_count() == 3
