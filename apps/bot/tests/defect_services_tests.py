"""The defect created from a finished form, run against the database."""

import pytest
from asgiref.sync import sync_to_async
from model_bakery import baker

from apps.bot.services.defect import create_defect
from apps.bot.user_data import DefectData
from apps.defects.constants import (
    DefectNode,
    DefectSeverity,
    DefectType,
    DefectVerdict,
)

make = sync_to_async(baker.make)


@pytest.mark.django_db(transaction=True)
class TestCreateDefect:
    async def test_the_inspector_verdict_is_saved_with_it(self):
        wagon = await make("core.Wagon", manufacture_year=2000)
        inspector = await make("core.Employee")
        form = DefectData(
            wagon_id=wagon.pk,
            node=DefectNode.WHEEL,
            defect_type=DefectType.WEAR,
            severity=DefectSeverity.HIGH,
            verdict=DefectVerdict.REPAIR_NOW,
        )

        defect = await create_defect(form, employee_id=inspector.pk)

        await sync_to_async(defect.refresh_from_db)()
        assert defect.verdict == DefectVerdict.REPAIR_NOW
        assert defect.ai_verdict == ""
