from datetime import timedelta

import pytest
from django.apps import apps as django_apps
from django.utils import timezone

from apps.core.mixins import UpdatedAtMixin
from apps.core.models import Employee

MONTH_AGO = timezone.now() - timedelta(days=30)


def _stamps_updated_at(model):
    field = getattr(getattr(model, "updated_at", None), "field", None)
    return getattr(field, "auto_now", False)


def test_every_model_stamping_updated_at_uses_the_mixin():
    stamped = [m for m in django_apps.get_models() if _stamps_updated_at(m)]

    assert stamped
    assert [m for m in stamped if not issubclass(m, UpdatedAtMixin)] == []


@pytest.fixture
def stale_employee(employee):
    Employee.objects.filter(pk=employee.pk).update(updated_at=MONTH_AGO)
    return employee


@pytest.mark.django_db
class TestPartialSave:
    def test_moves_updated_at(self, stale_employee):
        stale_employee.first_name = "Renamed"
        stale_employee.save(update_fields=["first_name"])

        stale_employee.refresh_from_db()
        assert stale_employee.updated_at > MONTH_AGO

    def test_leaves_unlisted_fields_unsaved(self, employee):
        last_name = employee.last_name
        employee.first_name = "Renamed"
        employee.last_name = "Renamed"
        employee.save(update_fields=["first_name"])

        employee.refresh_from_db()
        assert employee.last_name == last_name

    def test_saves_nothing_when_no_fields_are_listed(self, stale_employee):
        stale_employee.save(update_fields=[])

        stale_employee.refresh_from_db()
        assert stale_employee.updated_at == MONTH_AGO
