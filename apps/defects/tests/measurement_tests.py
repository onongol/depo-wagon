from decimal import Decimal

import pytest
from model_bakery import baker

from apps.defects.constants import MeasurementDimension
from apps.defects.models import DefectMeasurement


@pytest.mark.django_db
class TestDefectMeasurementModel:
    def test_create_measurement(self, defect):
        m = baker.make(
            DefectMeasurement, defect=defect, value=Decimal("10.50"), unit="mm"
        )
        assert m.pk is not None

    def test_str_contains_dimension_value_unit(self, defect):
        m = baker.make(
            DefectMeasurement,
            defect=defect,
            dimension=MeasurementDimension.DEPTH,
            value=Decimal("5.00"),
            unit="mm",
        )
        assert "5.00" in str(m)
        assert "mm" in str(m)

    def test_norm_value_null_by_default(self, defect):
        m = baker.make(DefectMeasurement, defect=defect, norm_value=None)
        assert m.norm_value is None

    def test_defect_deleted_cascades_measurement(self, defect):
        m = baker.make(DefectMeasurement, defect=defect)
        defect.delete()
        assert not DefectMeasurement.objects.filter(pk=m.pk).exists()

    def test_multiple_measurements_per_defect(self, defect):
        baker.make(DefectMeasurement, defect=defect, _quantity=3)
        assert defect.measurements.count() == 3


@pytest.mark.django_db
class TestDefectMeasurementIsExceeded:
    def test_no_norm_value_returns_false(self, defect):
        m = baker.make(
            DefectMeasurement, defect=defect, value=Decimal("10.00"), norm_value=None
        )
        assert m.is_exceeded is False

    def test_value_below_norm_returns_false(self, defect):
        m = baker.make(
            DefectMeasurement,
            defect=defect,
            value=Decimal("5.00"),
            norm_value=Decimal("10.00"),
        )
        assert m.is_exceeded is False

    def test_value_equal_to_norm_returns_false(self, defect):
        m = baker.make(
            DefectMeasurement,
            defect=defect,
            value=Decimal("10.00"),
            norm_value=Decimal("10.00"),
        )
        assert m.is_exceeded is False

    def test_value_above_norm_returns_true(self, defect):
        m = baker.make(
            DefectMeasurement,
            defect=defect,
            value=Decimal("15.00"),
            norm_value=Decimal("10.00"),
        )
        assert m.is_exceeded is True
