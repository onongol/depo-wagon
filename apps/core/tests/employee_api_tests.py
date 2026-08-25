import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from apps.core.constants import Department, EmployeeRole
from apps.core.models import Employee


@pytest.fixture
def employee_data():
    return {
        "employee_id": "987",
        "first_name": "Бат",
        "last_name": "Болд",
        "role": EmployeeRole.INSPECTOR,
    }


@pytest.mark.django_db
class TestEmployeeList:
    def test_list_returns_200(self, api_client):
        response = api_client.get(reverse("employee-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_list_returns_all_employees(self, api_client):
        baker.make("core.Employee", _quantity=3)
        response = api_client.get(reverse("employee-list"))
        assert response.data["count"] == Employee.objects.count()

    def test_list_uses_list_serializer(self, api_client, employee):
        response = api_client.get(reverse("employee-list"))
        result = next(
            r
            for r in response.data["results"]
            if r["employee_id"] == employee.employee_id
        )
        assert "phone" not in result
        assert "email" not in result
        assert "telegram_id" not in result
        assert "full_name" in result
        assert "role_display" in result
        assert "department" in result
        assert "department_display" in result


@pytest.mark.django_db
class TestEmployeeRetrieve:
    def test_retrieve_returns_200(self, api_client, employee):
        response = api_client.get(reverse("employee-detail", args=[employee.pk]))
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_not_found_returns_404(self, api_client):
        response = api_client.get(reverse("employee-detail", args=[99999]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_uses_full_serializer(self, api_client, employee):
        response = api_client.get(reverse("employee-detail", args=[employee.pk]))
        assert "phone" in response.data
        assert "email" in response.data
        assert "telegram_id" in response.data
        assert "short_name" in response.data
        assert "department" in response.data
        assert "department_display" in response.data


@pytest.mark.django_db
class TestEmployeeCreate:
    def test_create_returns_201(self, api_client, employee_data):
        response = api_client.post(
            reverse("employee-list"), employee_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_saves_to_db(self, api_client, employee_data):
        response = api_client.post(
            reverse("employee-list"), employee_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Employee.objects.filter(employee_id="987").exists()

    def test_create_duplicate_employee_id_returns_400(
        self, api_client, employee, employee_data
    ):
        employee_data["employee_id"] = employee.employee_id
        response = api_client.post(
            reverse("employee-list"), employee_data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestEmployeeUpdate:
    def test_patch_returns_200(self, api_client, employee):
        response = api_client.patch(
            reverse("employee-detail", args=[employee.pk]),
            {"role": EmployeeRole.MASTER},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_patch_updates_field(self, api_client, employee):
        response = api_client.patch(
            reverse("employee-detail", args=[employee.pk]),
            {"role": EmployeeRole.MASTER},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        employee.refresh_from_db()
        assert employee.role == EmployeeRole.MASTER


@pytest.mark.django_db
class TestEmployeeDelete:
    def test_delete_returns_204(self, api_client, employee):
        response = api_client.delete(reverse("employee-detail", args=[employee.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_removes_from_db(self, api_client, employee):
        pk = employee.pk
        api_client.delete(reverse("employee-detail", args=[pk]))
        assert not Employee.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestEmployeeFilters:
    def test_filter_by_role(self, api_client):
        baker.make("core.Employee", role=EmployeeRole.INSPECTOR, _quantity=2)
        baker.make("core.Employee", role=EmployeeRole.MASTER)
        response = api_client.get(
            reverse("employee-list"), {"role": EmployeeRole.INSPECTOR}
        )
        assert response.data["count"] == 2

    def test_filter_by_is_active(self, api_client):
        baker.make("core.Employee", is_active=True, _quantity=2)
        baker.make("core.Employee", is_active=False)
        response = api_client.get(reverse("employee-list"), {"is_active": "true"})
        assert response.data["count"] == Employee.objects.filter(is_active=True).count()

    def test_search_by_employee_id(self, api_client, employee):
        response = api_client.get(
            reverse("employee-list"), {"search": employee.employee_id}
        )
        assert response.data["count"] == 1
        result = next(
            r
            for r in response.data["results"]
            if r["employee_id"] == employee.employee_id
        )
        assert result["employee_id"] == employee.employee_id

    def test_filter_by_department(self, api_client):
        baker.make("core.Employee", department=Department.BOGIE, _quantity=2)
        baker.make("core.Employee", department=Department.WHEELSET)
        response = api_client.get(
            reverse("employee-list"), {"department": Department.BOGIE}
        )
        assert response.data["count"] == 2

    def test_ordering_by_employee_id(self, api_client):
        baker.make("core.Employee", employee_id="Z999")
        baker.make("core.Employee", employee_id="A001")
        response = api_client.get(reverse("employee-list"), {"ordering": "employee_id"})
        ids = [e["employee_id"] for e in response.data["results"]]
        assert ids.index("A001") < ids.index("Z999")
