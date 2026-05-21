import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from apps.core.constants import WagonStatus, WagonType


@pytest.fixture
def wagon_data():
    return {
        "number": "11111111",
        "wagon_type": WagonType.GONDOLA_CAR,
        "manufacture_year": 2010,
        "status": WagonStatus.ACTIVE,
    }


@pytest.mark.django_db
class TestWagonListPermissions:
    def test_anon_cannot_list(self, anon_client):
        response = anon_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_can_list(self, inspector_client):
        response = inspector_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_master_can_list(self, master_client):
        response = master_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_engineer_can_list(self, engineer_client):
        response = engineer_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_manager_can_list(self, manager_client):
        response = manager_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_list(self, superuser_client):
        response = superuser_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestWagonCreatePermissions:
    def test_anon_cannot_create(self, anon_client, wagon_data):
        response = anon_client.post(reverse("wagon-list"), wagon_data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_create(self, inspector_client, wagon_data):
        response = inspector_client.post(
            reverse("wagon-list"), wagon_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_create(self, master_client, wagon_data):
        response = master_client.post(reverse("wagon-list"), wagon_data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_engineer_can_create(self, engineer_client, wagon_data):
        response = engineer_client.post(
            reverse("wagon-list"), wagon_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_manager_can_create(self, manager_client, wagon_data):
        response = manager_client.post(reverse("wagon-list"), wagon_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_superuser_can_create(self, superuser_client, wagon_data):
        response = superuser_client.post(
            reverse("wagon-list"), wagon_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestWagonUpdatePermissions:
    def test_anon_cannot_update(self, anon_client, wagon):
        response = anon_client.patch(
            reverse("wagon-detail", args=[wagon.pk]),
            {"status": WagonStatus.REPAIR},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_update(self, inspector_client, wagon):
        response = inspector_client.patch(
            reverse("wagon-detail", args=[wagon.pk]),
            {"status": WagonStatus.REPAIR},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_update(self, master_client, wagon):
        response = master_client.patch(
            reverse("wagon-detail", args=[wagon.pk]),
            {"status": WagonStatus.REPAIR},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_engineer_can_update(self, engineer_client, wagon):
        response = engineer_client.patch(
            reverse("wagon-detail", args=[wagon.pk]),
            {"status": WagonStatus.REPAIR},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_manager_can_update(self, manager_client, wagon):
        response = manager_client.patch(
            reverse("wagon-detail", args=[wagon.pk]),
            {"status": WagonStatus.REPAIR},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_update(self, superuser_client, wagon):
        response = superuser_client.patch(
            reverse("wagon-detail", args=[wagon.pk]),
            {"status": WagonStatus.REPAIR},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestWagonDeletePermissions:
    def test_anon_cannot_delete(self, anon_client, wagon):
        response = anon_client.delete(reverse("wagon-detail", args=[wagon.pk]))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_delete(self, inspector_client, wagon):
        response = inspector_client.delete(reverse("wagon-detail", args=[wagon.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_delete(self, master_client, wagon):
        response = master_client.delete(reverse("wagon-detail", args=[wagon.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_engineer_can_delete(self, engineer_client, wagon):
        response = engineer_client.delete(reverse("wagon-detail", args=[wagon.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_manager_can_delete(self, manager_client, wagon):
        wagon2 = baker.make("core.Wagon", manufacture_year=2000)
        response = manager_client.delete(reverse("wagon-detail", args=[wagon2.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_superuser_can_delete(self, superuser_client, wagon):
        response = superuser_client.delete(reverse("wagon-detail", args=[wagon.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestWagonNoEmployeePermissions:
    def test_cannot_list(self, no_employee_client):
        response = no_employee_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_create(self, no_employee_client, wagon_data):
        response = no_employee_client.post(
            reverse("wagon-list"), wagon_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_update(self, no_employee_client, wagon):
        response = no_employee_client.patch(
            reverse("wagon-detail", args=[wagon.pk]),
            {"status": WagonStatus.REPAIR},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_delete(self, no_employee_client, wagon):
        response = no_employee_client.delete(reverse("wagon-detail", args=[wagon.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN
