from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError

from apps.core.constants import WagonStatus, WagonType
from apps.core.models import Wagon


def make_wagon(**kwargs):
    defaults = {
        "number": "12345678",
        "wagon_type": WagonType.GONDOLA_CAR,
        "manufacture_year": 2000,
        "status": WagonStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Wagon(**defaults)


@pytest.mark.django_db
class TestWagonModel:
    def test_str(self):
        wagon = make_wagon(number="12345678")
        assert "12345678" in str(wagon)

    def test_default_status(self):
        wagon = make_wagon()
        assert wagon.status == WagonStatus.ACTIVE

    def test_default_mileage(self):
        wagon = make_wagon()
        assert wagon.mileage_km == 0

    def test_save_and_retrieve(self):
        wagon = make_wagon()
        wagon.save()
        assert Wagon.objects.filter(number="12345678").exists()

    def test_number_is_unique(self):
        make_wagon(number="11111111").save()
        with pytest.raises(Exception):
            make_wagon(number="11111111").save()


@pytest.mark.django_db
class TestWagonClean:
    def test_last_repair_before_manufacture_year_raises(self):
        wagon = make_wagon(
            manufacture_year=2000,
            last_repair_date=date(1999, 1, 1),
        )
        with pytest.raises(ValidationError, match="Last repair date"):
            wagon.full_clean()

    def test_next_repair_before_last_repair_raises(self):
        wagon = make_wagon(
            last_repair_date=date(2020, 6, 1),
            next_repair_date=date(2020, 1, 1),
        )
        with pytest.raises(ValidationError, match="Next repair date"):
            wagon.full_clean()

    def test_next_repair_equal_last_repair_raises(self):
        wagon = make_wagon(
            last_repair_date=date(2020, 6, 1),
            next_repair_date=date(2020, 6, 1),
        )
        with pytest.raises(ValidationError):
            wagon.full_clean()

    def test_valid_dates_pass(self):
        wagon = make_wagon(
            manufacture_year=2000,
            last_repair_date=date(2020, 1, 1),
            next_repair_date=date(2023, 1, 1),
        )
        wagon.full_clean()  # Should not raise


@pytest.mark.django_db
class TestWagonNeedsRepairSoon:
    def test_no_next_repair_date(self):
        wagon = make_wagon()
        assert wagon.needs_repair_soon is False

    def test_repair_within_30_days(self):
        wagon = make_wagon(next_repair_date=date.today() + timedelta(days=10))
        assert wagon.needs_repair_soon is True

    def test_repair_today(self):
        wagon = make_wagon(next_repair_date=date.today())
        assert wagon.needs_repair_soon is True

    def test_repair_far_future(self):
        wagon = make_wagon(next_repair_date=date.today() + timedelta(days=90))
        assert wagon.needs_repair_soon is False
