import uuid

import pytest
from model_bakery import baker

from apps.defects.constants import DefectStatus, DefectVerdict
from apps.defects.models import Defect


@pytest.mark.django_db
class TestDefectModel:
    def test_create_defect(self, defect):
        assert defect.pk is not None

    def test_id_is_uuid(self, defect):
        assert isinstance(defect.pk, uuid.UUID)

    def test_default_status_is_open(self, defect):
        assert defect.status == DefectStatus.OPEN

    def test_str_contains_node_and_defect(self, defect):
        assert "—" in str(defect)

    def test_wagon_deleted_cascades_defect(self, defect):
        wagon = defect.wagon
        wagon.delete()
        assert not Defect.objects.filter(pk=defect.pk).exists()

    def test_inspector_deleted_sets_null(self, defect):
        inspector = defect.inspector
        inspector.delete()
        defect.refresh_from_db()
        assert defect.inspector is None


@pytest.mark.django_db
class TestDefectIsRepaired:
    def test_open_is_not_repaired(self, wagon):
        defect = baker.make(Defect, wagon=wagon, status=DefectStatus.OPEN)
        assert defect.is_repaired is False

    def test_in_progress_is_not_repaired(self, wagon):
        defect = baker.make(Defect, wagon=wagon, status=DefectStatus.IN_PROGRESS)
        assert defect.is_repaired is False

    def test_resolved_is_repaired(self, wagon):
        defect = baker.make(Defect, wagon=wagon, status=DefectStatus.RESOLVED)
        assert defect.is_repaired is True

    def test_closed_is_not_repaired(self, wagon):
        defect = baker.make(Defect, wagon=wagon, status=DefectStatus.CLOSED)
        assert defect.is_repaired is False


@pytest.mark.django_db
class TestDefectVerdict:
    def test_verdict_empty_by_default(self, defect):
        assert defect.verdict == ""

    def test_ai_verdict_empty_by_default(self, defect):
        assert defect.ai_verdict == ""

    def test_set_verdict(self, wagon):
        defect = baker.make(Defect, wagon=wagon, verdict=DefectVerdict.REPAIR_NOW)
        assert defect.verdict == DefectVerdict.REPAIR_NOW


@pytest.mark.django_db
class TestDefectNullableFields:
    def test_repaired_at_null_by_default(self, defect):
        assert defect.repaired_at is None

    def test_ai_confidence_null_by_default(self, defect):
        assert defect.ai_confidence is None

    def test_multiple_defects_per_wagon(self, wagon):
        baker.make(Defect, wagon=wagon, _quantity=3)
        assert wagon.defects.count() == 3
