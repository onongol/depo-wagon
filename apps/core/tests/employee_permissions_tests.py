import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from apps.core.constants import EmployeeRole

User = get_user_model()


@pytest.fixture
def employee_data(db):
    user = User.objects.create_user(email="newstaff@depot.mn", password="pass123")
    return {
        "user": user.pk,
        "first_name": "Bat",
        "last_name": "Erdene",
        "employee_id": "EMP-9999",
        "role": EmployeeRole.INSPECTOR,
    }


@pytest.mark.django_db
class TestEmployeeListPermissions:
    def test_anon_cannot_list(self, anon_client):
        response = anon_client.get(reverse("employee-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_list(self, inspector_client):
        response = inspector_client.get(reverse("employee-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_list(self, master_client):
        response = master_client.get(reverse("employee-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_engineer_can_list(self, engineer_client):
        response = engineer_client.get(reverse("employee-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_manager_can_list(self, manager_client):
        response = manager_client.get(reverse("employee-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_list(self, superuser_client):
        response = superuser_client.get(reverse("employee-list"))
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestEmployeeCreatePermissions:
    def test_anon_cannot_create(self, anon_client, employee_data):
        response = anon_client.post(
            reverse("employee-list"), employee_data, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_create(self, inspector_client, employee_data):
        response = inspector_client.post(
            reverse("employee-list"), employee_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_create(self, master_client, employee_data):
        response = master_client.post(
            reverse("employee-list"), employee_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_engineer_cannot_create(self, engineer_client, employee_data):
        response = engineer_client.post(
            reverse("employee-list"), employee_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_cannot_create(self, manager_client, employee_data):
        response = manager_client.post(
            reverse("employee-list"), employee_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_create(self, superuser_client, employee_data):
        response = superuser_client.post(
            reverse("employee-list"), employee_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestEmployeeUpdatePermissions:
    def test_anon_cannot_update(self, anon_client, employee):
        response = anon_client.patch(
            reverse("employee-detail", args=[employee.pk]),
            {"first_name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_update(self, inspector_client, employee):
        response = inspector_client.patch(
            reverse("employee-detail", args=[employee.pk]),
            {"first_name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_update(self, master_client, employee):
        response = master_client.patch(
            reverse("employee-detail", args=[employee.pk]),
            {"first_name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_engineer_cannot_update(self, engineer_client, employee):
        response = engineer_client.patch(
            reverse("employee-detail", args=[employee.pk]),
            {"first_name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_cannot_update(self, manager_client, employee):
        response = manager_client.patch(
            reverse("employee-detail", args=[employee.pk]),
            {"first_name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_update(self, superuser_client, employee):
        response = superuser_client.patch(
            reverse("employee-detail", args=[employee.pk]),
            {"first_name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestEmployeeDeletePermissions:
    def test_anon_cannot_delete(self, anon_client, employee):
        response = anon_client.delete(reverse("employee-detail", args=[employee.pk]))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_delete(self, inspector_client, employee):
        response = inspector_client.delete(
            reverse("employee-detail", args=[employee.pk])
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_delete(self, master_client, employee):
        response = master_client.delete(reverse("employee-detail", args=[employee.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_engineer_cannot_delete(self, engineer_client, employee):
        response = engineer_client.delete(
            reverse("employee-detail", args=[employee.pk])
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_cannot_delete(self, manager_client, employee):
        response = manager_client.delete(reverse("employee-detail", args=[employee.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_delete(self, superuser_client, employee):
        employee2 = baker.make("core.Employee")
        response = superuser_client.delete(
            reverse("employee-detail", args=[employee2.pk])
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestEmployeeNoEmployeePermissions:
    def test_cannot_list(self, no_employee_client):
        response = no_employee_client.get(reverse("employee-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_create(self, no_employee_client, employee_data):
        response = no_employee_client.post(
            reverse("employee-list"), employee_data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_update(self, no_employee_client, employee):
        response = no_employee_client.patch(
            reverse("employee-detail", args=[employee.pk]),
            {"first_name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_delete(self, no_employee_client, employee):
        response = no_employee_client.delete(
            reverse("employee-detail", args=[employee.pk])
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
