import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework import status

from apps.core.constants import EmployeeRole
from apps.defects.constants import DefectNode, DefectSeverity, DefectStatus, DefectType

User = get_user_model()


@pytest.fixture
def inspector_employee(db):
    user = User.objects.create_user(email="insp2@depot.mn", password="pass123")
    return baker.make("core.Employee", user=user, role=EmployeeRole.INSPECTOR)


@pytest.fixture
def defect(db, wagon, inspector_employee):
    return baker.make("defects.Defect", wagon=wagon, inspector=inspector_employee)


@pytest.fixture
def defect_data(wagon, inspector_employee):
    return {
        "wagon": wagon.pk,
        "inspector": inspector_employee.pk,
        "node": DefectNode.WHEELSET,
        "defect": DefectType.CRACK,
        "severity": DefectSeverity.MEDIUM,
        "status": DefectStatus.OPEN,
        "inspected_at": timezone.now().isoformat(),
    }


@pytest.mark.django_db
class TestDefectListPermissions:
    def test_anon_cannot_list(self, anon_client):
        response = anon_client.get(reverse("defect-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_can_list(self, inspector_client):
        response = inspector_client.get(reverse("defect-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_master_can_list(self, master_client):
        response = master_client.get(reverse("defect-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_engineer_can_list(self, engineer_client):
        response = engineer_client.get(reverse("defect-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_manager_can_list(self, manager_client):
        response = manager_client.get(reverse("defect-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_list(self, superuser_client):
        response = superuser_client.get(reverse("defect-list"))
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestDefectCreatePermissions:
    def test_anon_cannot_create(self, anon_client, defect_data):
        response = anon_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_master_cannot_create(self, master_client, defect_data):
        response = master_client.post(
            reverse("defect-list"), defect_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_cannot_create(self, manager_client, defect_data):
        response = manager_client.post(
            reverse("defect-list"), defect_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_inspector_can_create(self, inspector_client, defect_data):
        response = inspector_client.post(
            reverse("defect-list"), defect_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_engineer_can_create(self, engineer_client, defect_data):
        response = engineer_client.post(
            reverse("defect-list"), defect_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_superuser_can_create(self, superuser_client, defect_data):
        response = superuser_client.post(
            reverse("defect-list"), defect_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestDefectUpdatePermissions:
    def test_anon_cannot_update(self, anon_client, defect):
        response = anon_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"status": DefectStatus.CLOSED},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_update(self, inspector_client, defect):
        response = inspector_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"status": DefectStatus.CLOSED},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_update(self, master_client, defect):
        response = master_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"status": DefectStatus.CLOSED},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_cannot_update(self, manager_client, defect):
        response = manager_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"status": DefectStatus.CLOSED},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_engineer_can_update(self, engineer_client, defect):
        response = engineer_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"status": DefectStatus.CLOSED},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_update(self, superuser_client, defect):
        response = superuser_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"status": DefectStatus.CLOSED},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestDefectDeletePermissions:
    def test_anon_cannot_delete(self, anon_client, defect):
        response = anon_client.delete(reverse("defect-detail", args=[defect.pk]))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_delete(self, inspector_client, defect):
        response = inspector_client.delete(reverse("defect-detail", args=[defect.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_delete(self, master_client, defect):
        response = master_client.delete(reverse("defect-detail", args=[defect.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_cannot_delete(self, manager_client, defect):
        response = manager_client.delete(reverse("defect-detail", args=[defect.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_engineer_can_delete(self, engineer_client, defect):
        response = engineer_client.delete(reverse("defect-detail", args=[defect.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_superuser_can_delete(self, superuser_client, wagon, inspector_employee):
        defect2 = baker.make(
            "defects.Defect", wagon=wagon, inspector=inspector_employee
        )
        response = superuser_client.delete(reverse("defect-detail", args=[defect2.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestDefectNoEmployeePermissions:
    def test_cannot_list(self, no_employee_client):
        response = no_employee_client.get(reverse("defect-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_create(self, no_employee_client, defect_data):
        response = no_employee_client.post(
            reverse("defect-list"), defect_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_update(self, no_employee_client, defect):
        response = no_employee_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"status": DefectStatus.CLOSED},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_delete(self, no_employee_client, defect):
        response = no_employee_client.delete(reverse("defect-detail", args=[defect.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN
