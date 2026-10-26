from unittest.mock import patch

import pytest
from model_bakery import baker

from apps.defects.constants import DefectStatus, DefectVerdict

DELAY = "apps.ai_service.tasks.embed_defect_task.delay"


@pytest.mark.django_db
class TestOnDefectClosed:
    def _make_defect(self, **kwargs):
        return baker.make("defects.Defect", wagon__manufacture_year=2020, **kwargs)

    def test_queues_task_when_status_becomes_closed(
        self, django_capture_on_commit_callbacks
    ):
        defect = self._make_defect(
            status=DefectStatus.OPEN, verdict=DefectVerdict.REPAIR_NOW
        )

        with (
            patch(DELAY) as mock_delay,
            django_capture_on_commit_callbacks(execute=True),
        ):
            defect.status = DefectStatus.CLOSED
            defect.save()

        mock_delay.assert_called_once_with(str(defect.id))

    def test_queues_task_when_closed_without_verdict_in_memory(
        self, django_capture_on_commit_callbacks
    ):
        """Signal fires on an empty verdict; the task reads it fresh from the DB."""
        defect = self._make_defect(
            status=DefectStatus.OPEN, verdict=DefectVerdict.REPAIR_NOW
        )

        with (
            patch(DELAY) as mock_delay,
            django_capture_on_commit_callbacks(execute=True),
        ):
            defect.status = DefectStatus.CLOSED
            defect.verdict = ""  # stale in-memory value, DB still has the verdict
            defect.save(update_fields=["status"])

        mock_delay.assert_called_once_with(str(defect.id))

    def test_waits_for_the_commit(self, django_capture_on_commit_callbacks):
        defect = self._make_defect(
            status=DefectStatus.OPEN, verdict=DefectVerdict.REPAIR_NOW
        )

        with (
            patch(DELAY) as mock_delay,
            django_capture_on_commit_callbacks() as callbacks,
        ):
            defect.status = DefectStatus.CLOSED
            defect.save()

            mock_delay.assert_not_called()

        assert len(callbacks) == 1

    def test_does_not_queue_when_not_closed(self, django_capture_on_commit_callbacks):
        defect = self._make_defect(
            status=DefectStatus.OPEN, verdict=DefectVerdict.REPAIR_NOW
        )

        with (
            patch(DELAY) as mock_delay,
            django_capture_on_commit_callbacks(execute=True),
        ):
            defect.save()

        mock_delay.assert_not_called()
