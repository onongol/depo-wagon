"""The status updates, run against the database."""

import uuid

import pytest
from asgiref.sync import sync_to_async
from model_bakery import baker

from apps.bot.services.defect import update_any_defect_status, update_defect_status
from apps.defects.constants import DefectStatus

make = sync_to_async(baker.make)


async def _defect(**fields):
    wagon = await make("core.Wagon", manufacture_year=2000)
    defaults = {"wagon": wagon, "status": DefectStatus.OPEN}
    return await make("defects.Defect", **(defaults | fields))


async def _status(defect):
    await sync_to_async(defect.refresh_from_db)()
    return defect.status


@pytest.mark.django_db(transaction=True)
class TestUpdateDefectStatus:
    async def test_saves_the_status_on_their_own_defect(self):
        mine = await make("core.Employee")
        defect = await _defect(inspector=mine)

        saved = await update_defect_status(
            defect.pk, DefectStatus.IN_PROGRESS, employee_id=mine.pk
        )

        assert saved is True
        assert await _status(defect) == DefectStatus.IN_PROGRESS

    async def test_closing_stamps_repaired_at(self):
        mine = await make("core.Employee")
        defect = await _defect(inspector=mine)

        await update_defect_status(defect.pk, DefectStatus.CLOSED, employee_id=mine.pk)

        await sync_to_async(defect.refresh_from_db)()
        assert defect.repaired_at is not None

    async def test_leaves_another_employees_defect_alone(self):
        mine = await make("core.Employee")
        other = await make("core.Employee")
        defect = await _defect(inspector=other)

        saved = await update_defect_status(
            defect.pk, DefectStatus.CLOSED, employee_id=mine.pk
        )

        assert saved is False
        assert await _status(defect) == DefectStatus.OPEN

    async def test_leaves_a_defect_with_no_inspector_alone(self):
        mine = await make("core.Employee")
        defect = await _defect(inspector=None)

        saved = await update_defect_status(
            defect.pk, DefectStatus.CLOSED, employee_id=mine.pk
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


@pytest.mark.django_db(transaction=True)
class TestUpdateAnyDefectStatus:
    async def test_saves_the_status_on_anyones_defect(self):
        defect = await _defect(inspector=await make("core.Employee"))

        assert await update_any_defect_status(defect.pk, DefectStatus.CLOSED) is True
        assert await _status(defect) == DefectStatus.CLOSED

    async def test_a_missing_defect_is_reported(self):
        assert (
            await update_any_defect_status(uuid.uuid4(), DefectStatus.CLOSED) is False
        )
