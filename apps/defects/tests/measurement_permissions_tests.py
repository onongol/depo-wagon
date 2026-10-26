import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from apps.defects.constants import MeasurementDimension


@pytest.fixture
def measurement(db, defect):
    return baker.make("defects.DefectMeasurement", defect=defect)


@pytest.fixture
def measurement_data(defect):
    return {
        "defect": str(defect.pk),
        "dimension": MeasurementDimension.LENGTH,
        "value": 12.5,
        "unit": "mm",
    }


@pytest.mark.django_db
class TestMeasurementListPermissions:
    def test_anon_cannot_list(self, anon_client):
        response = anon_client.get(reverse("measurement-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_can_list(self, inspector_client):
        response = inspector_client.get(reverse("measurement-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_master_can_list(self, master_client):
        response = master_client.get(reverse("measurement-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_engineer_can_list(self, engineer_client):
        response = engineer_client.get(reverse("measurement-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_manager_can_list(self, manager_client):
        response = manager_client.get(reverse("measurement-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_list(self, superuser_client):
        response = superuser_client.get(reverse("measurement-list"))
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestMeasurementCreatePermissions:
    def test_anon_cannot_create(self, anon_client, measurement_data):
        response = anon_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_master_cannot_create(self, master_client, measurement_data):
        response = master_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_create(self, manager_client, measurement_data):
        response = manager_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_inspector_can_create_on_their_own_defect(
        self, inspector_client, measurement_data, wagon
    ):
        own = baker.make(
            "defects.Defect", wagon=wagon, inspector=inspector_client.employee
        )
        response = inspector_client.post(
            reverse("measurement-list"),
            measurement_data | {"defect": str(own.pk)},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_inspector_cannot_create_on_another_inspectors_defect(
        self, inspector_client, measurement_data
    ):
        response = inspector_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "defect" in response.data

    def test_engineer_can_create(self, engineer_client, measurement_data):
        response = engineer_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_superuser_can_create(self, superuser_client, measurement_data):
        response = superuser_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestMeasurementUpdatePermissions:
    def test_anon_cannot_update(self, anon_client, measurement):
        response = anon_client.patch(
            reverse("measurement-detail", args=[measurement.pk]),
            {"value": 99.0},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_update(self, inspector_client, measurement):
        response = inspector_client.patch(
            reverse("measurement-detail", args=[measurement.pk]),
            {"value": 99.0},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_update(self, master_client, measurement):
        response = master_client.patch(
            reverse("measurement-detail", args=[measurement.pk]),
            {"value": 99.0},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_update(self, manager_client, measurement):
        response = manager_client.patch(
            reverse("measurement-detail", args=[measurement.pk]),
            {"value": 99.0},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_engineer_can_update(self, engineer_client, measurement):
        response = engineer_client.patch(
            reverse("measurement-detail", args=[measurement.pk]),
            {"value": 99.0},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_update(self, superuser_client, measurement):
        response = superuser_client.patch(
            reverse("measurement-detail", args=[measurement.pk]),
            {"value": 99.0},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestMeasurementDeletePermissions:
    def test_anon_cannot_delete(self, anon_client, measurement):
        response = anon_client.delete(
            reverse("measurement-detail", args=[measurement.pk])
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_delete(self, inspector_client, measurement):
        response = inspector_client.delete(
            reverse("measurement-detail", args=[measurement.pk])
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_delete(self, master_client, measurement):
        response = master_client.delete(
            reverse("measurement-detail", args=[measurement.pk])
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_delete(self, manager_client, measurement):
        response = manager_client.delete(
            reverse("measurement-detail", args=[measurement.pk])
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_engineer_can_delete(self, engineer_client, measurement):
        response = engineer_client.delete(
            reverse("measurement-detail", args=[measurement.pk])
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_superuser_can_delete(self, superuser_client, defect):
        measurement2 = baker.make("defects.DefectMeasurement", defect=defect)
        response = superuser_client.delete(
            reverse("measurement-detail", args=[measurement2.pk])
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestMeasurementNoEmployeePermissions:
    def test_cannot_list(self, no_employee_client):
        response = no_employee_client.get(reverse("measurement-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_create(self, no_employee_client, measurement_data):
        response = no_employee_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_update(self, no_employee_client, measurement):
        response = no_employee_client.patch(
            reverse("measurement-detail", args=[measurement.pk]),
            {"value": 99.0},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_delete(self, no_employee_client, measurement):
        response = no_employee_client.delete(
            reverse("measurement-detail", args=[measurement.pk])
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
