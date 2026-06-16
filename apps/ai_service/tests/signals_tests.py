from unittest.mock import patch

import pytest
from model_bakery import baker

from apps.defects.constants import DefectStatus, DefectVerdict


@pytest.mark.django_db
class TestOnDefectClosed:
    def _make_defect(self, **kwargs):
        return baker.make("defects.Defect", wagon__manufacture_year=2020, **kwargs)

    def test_queues_task_when_closed_with_verdict(self):
        defect = self._make_defect(status=DefectStatus.OPEN, verdict="")

        with patch("apps.ai_service.tasks.embed_defect_task.delay") as mock_delay:
            defect.status = DefectStatus.CLOSED
            defect.verdict = DefectVerdict.REPAIR_NOW
            defect.save()

        mock_delay.assert_called_once_with(str(defect.id))

    def test_does_not_queue_when_not_closed(self):
        defect = self._make_defect(status=DefectStatus.OPEN, verdict=DefectVerdict.REPAIR_NOW)

        with patch("apps.ai_service.tasks.embed_defect_task.delay") as mock_delay:
            defect.save()

        mock_delay.assert_not_called()

    def test_does_not_queue_when_closed_without_verdict(self):
        defect = self._make_defect(status=DefectStatus.OPEN, verdict="")

        with patch("apps.ai_service.tasks.embed_defect_task.delay") as mock_delay:
            defect.status = DefectStatus.CLOSED
            defect.verdict = ""
            defect.save()

        mock_delay.assert_not_called()
