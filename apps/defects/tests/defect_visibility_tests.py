"""Who sees which defects: engineers and managers all, everyone else their own."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from apps.core.constants import EmployeeRole
from apps.defects.models import Defect
from conftest import make_client_with_role

SCOPED_ROLES = [EmployeeRole.INSPECTOR, EmployeeRole.MASTER, EmployeeRole.WORKER]
ALL_ROLES = [EmployeeRole.ENGINEER, EmployeeRole.MANAGER]


@pytest.fixture
def others_defect(db, wagon):
    return baker.make(
        "defects.Defect", wagon=wagon, inspector=baker.make("core.Employee")
    )


@pytest.fixture
def orphan_defect(db, wagon):
    return baker.make("defects.Defect", wagon=wagon, inspector=None)


def _own_defect(client, wagon):
    return baker.make("defects.Defect", wagon=wagon, inspector=client.employee)


def _ids(response):
    return {str(row["id"]) for row in response.data["results"]}


@pytest.mark.django_db
class TestDefectEndpoints:
    @pytest.mark.parametrize("role", SCOPED_ROLES)
    def test_lists_only_their_own(self, role, wagon, others_defect, orphan_defect):
        client = make_client_with_role(role)
        own = _own_defect(client, wagon)

        response = client.get(reverse("defect-list"))

        assert response.status_code == status.HTTP_200_OK
        assert _ids(response) == {str(own.pk)}

    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_lists_every_defect(self, role, wagon, others_defect, orphan_defect):
        client = make_client_with_role(role)
        own = _own_defect(client, wagon)

        response = client.get(reverse("defect-list"))

        assert _ids(response) == {
            str(own.pk),
            str(others_defect.pk),
            str(orphan_defect.pk),
        }

    def test_superuser_lists_every_defect(
        self, superuser_client, others_defect, orphan_defect
    ):
        response = superuser_client.get(reverse("defect-list"))

        assert _ids(response) == {str(others_defect.pk), str(orphan_defect.pk)}

    @pytest.mark.parametrize("role", SCOPED_ROLES)
    def test_another_employees_defect_is_not_found(self, role, others_defect):
        client = make_client_with_role(role)

        response = client.get(reverse("defect-detail", args=[others_defect.pk]))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_another_employees_defect_is_found(self, role, others_defect):
        client = make_client_with_role(role)

        response = client.get(reverse("defect-detail", args=[others_defect.pk]))

        assert response.status_code == status.HTTP_200_OK

    def test_filters_cannot_widen_the_scope(self, inspector_client, others_defect):
        response = inspector_client.get(
            reverse("defect-list"), {"wagon": others_defect.wagon_id}
        )

        assert _ids(response) == set()


@pytest.mark.django_db
class TestMeasurementAndPhotoEndpoints:
    @pytest.mark.parametrize(
        ("model", "list_name", "detail_name"),
        [
            ("defects.DefectMeasurement", "measurement-list", "measurement-detail"),
            ("defects.DefectPhoto", "photo-list", "photo-detail"),
        ],
    )
    def test_follow_the_defect(
        self, model, list_name, detail_name, wagon, others_defect
    ):
        inspector = make_client_with_role(EmployeeRole.INSPECTOR)
        engineer = make_client_with_role(EmployeeRole.ENGINEER)
        mine = baker.make(model, defect=_own_defect(inspector, wagon))
        theirs = baker.make(model, defect=others_defect)

        assert _ids(inspector.get(reverse(list_name))) == {str(mine.pk)}
        assert (
            inspector.get(reverse(detail_name, args=[theirs.pk])).status_code
            == status.HTTP_404_NOT_FOUND
        )
        assert _ids(engineer.get(reverse(list_name))) == {str(mine.pk), str(theirs.pk)}


@pytest.mark.django_db
class TestVisibleTo:
    def test_an_anonymous_user_sees_nothing(self, others_defect):
        assert not Defect.objects.visible_to(AnonymousUser()).exists()

    def test_a_user_without_an_employee_sees_nothing(
        self, django_user_model, others_defect
    ):
        user = django_user_model.objects.create_user(email="x@depot.mn", password="p")

        assert not Defect.objects.visible_to(user).exists()


@pytest.mark.django_db
class TestWebDefectList:
    def _defects(self, client):
        response = client.get(reverse("web:defect_list"))
        assert response.status_code == 200
        return {d.pk for d in response.context["defects"]}

    def test_an_inspector_sees_only_their_own(self, client, wagon, others_defect):
        inspector = make_client_with_role(EmployeeRole.INSPECTOR)
        own = _own_defect(inspector, wagon)
        client.force_login(inspector.employee.user)

        assert self._defects(client) == {own.pk}

    def test_a_manager_sees_every_defect(self, client, wagon, others_defect):
        manager = make_client_with_role(EmployeeRole.MANAGER)
        own = _own_defect(manager, wagon)
        client.force_login(manager.employee.user)

        assert self._defects(client) == {own.pk, others_defect.pk}
