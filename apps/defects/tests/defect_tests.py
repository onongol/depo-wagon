import uuid

import pytest
from model_bakery import baker

from apps.core.constants import Department
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

    def test_closed_is_repaired(self, wagon):
        defect = baker.make(Defect, wagon=wagon, status=DefectStatus.CLOSED)
        assert defect.is_repaired is True


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


@pytest.mark.django_db
class TestDefectPartNumber:
    def test_part_number_blank_by_default(self, defect):
        assert defect.part_number == ""

    def test_part_number_can_be_set(self, wagon):
        defect = baker.make(Defect, wagon=wagon, part_number="PN-12345")
        defect.refresh_from_db()
        assert defect.part_number == "PN-12345"

    def test_part_number_is_optional(self, wagon):
        defect = baker.make(Defect, wagon=wagon)
        defect.refresh_from_db()
        assert defect.part_number == ""


@pytest.mark.django_db
class TestDefectDepartment:
    def test_department_blank_by_default(self, defect):
        assert defect.department == ""

    def test_department_can_be_set(self, wagon):
        defect = baker.make(Defect, wagon=wagon, department=Department.REPAIR_1)
        assert defect.department == Department.REPAIR_1

    def test_responsible_employee_null_by_default(self, defect):
        assert defect.responsible_employee is None

    def test_responsible_employee_can_be_set(self, wagon):
        responsible = baker.make("core.Employee", department=Department.REPAIR_1)
        defect = baker.make(Defect, wagon=wagon, responsible_employee=responsible)
        defect.refresh_from_db()
        assert defect.responsible_employee_id == responsible.pk

    def test_responsible_employee_deleted_sets_null(self, wagon):
        responsible = baker.make("core.Employee")
        defect = baker.make(Defect, wagon=wagon, responsible_employee=responsible)
        responsible.delete()
        defect.refresh_from_db()
        assert defect.responsible_employee is None
