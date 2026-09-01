import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from apps.core.constants import Department, EmployeeRole

User = get_user_model()


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="worker@depot.mn", password="pass123")


@pytest.mark.django_db
class TestUserList:
    def test_list_returns_200(self, superuser_client):
        response = superuser_client.get(reverse("user-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_list_returns_all_users(self, superuser_client, other_user):
        baker.make(User, _quantity=3)
        response = superuser_client.get(reverse("user-list"))
        assert response.data["count"] == User.objects.count()

    def test_list_uses_list_serializer(self, superuser_client, other_user):
        response = superuser_client.get(reverse("user-list"))
        result = next(
            r for r in response.data["results"] if r["email"] == other_user.email
        )
        assert "date_joined" not in result
        assert "employee" not in result
        assert "password" not in result
        assert result["is_active"] is True


@pytest.mark.django_db
class TestUserRetrieve:
    def test_retrieve_returns_200(self, superuser_client, other_user):
        response = superuser_client.get(reverse("user-detail", args=[other_user.pk]))
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_not_found_returns_404(self, superuser_client):
        response = superuser_client.get(reverse("user-detail", args=[99999]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_uses_full_serializer(self, superuser_client, other_user):
        response = superuser_client.get(reverse("user-detail", args=[other_user.pk]))
        assert response.data["email"] == other_user.email
        assert "date_joined" in response.data
        assert "last_login" in response.data
        assert "is_superuser" in response.data
        assert "password" not in response.data

    def test_retrieve_includes_employee(self, superuser_client, other_user):
        baker.make(
            "core.Employee",
            user=other_user,
            role=EmployeeRole.INSPECTOR,
            department=Department.BOGIE,
        )
        response = superuser_client.get(reverse("user-detail", args=[other_user.pk]))
        assert response.data["employee"]["role"] == EmployeeRole.INSPECTOR
        assert response.data["employee"]["role_display"]
        assert response.data["employee"]["department_display"]

    def test_retrieve_without_employee_returns_null(self, superuser_client, other_user):
        response = superuser_client.get(reverse("user-detail", args=[other_user.pk]))
        assert response.data["employee"] is None


@pytest.mark.django_db
class TestUserFilters:
    def test_filter_by_is_active(self, superuser_client):
        baker.make(User, is_active=True, _quantity=2)
        baker.make(User, is_active=False)
        response = superuser_client.get(reverse("user-list"), {"is_active": "true"})
        assert response.data["count"] == User.objects.filter(is_active=True).count()

    def test_filter_by_is_staff(self, superuser_client, other_user):
        response = superuser_client.get(reverse("user-list"), {"is_staff": "false"})
        emails = [u["email"] for u in response.data["results"]]
        assert other_user.email in emails
        assert "admin@depot.mn" not in emails

    def test_search_by_email(self, superuser_client, other_user):
        response = superuser_client.get(reverse("user-list"), {"search": "worker"})
        assert response.data["count"] == 1
        assert response.data["results"][0]["email"] == other_user.email

    def test_ordering_by_email(self, superuser_client):
        baker.make(User, email="zulu@depot.mn")
        baker.make(User, email="alpha@depot.mn")
        response = superuser_client.get(reverse("user-list"), {"ordering": "email"})
        emails = [u["email"] for u in response.data["results"]]
        assert emails.index("alpha@depot.mn") < emails.index("zulu@depot.mn")


@pytest.mark.django_db
class TestUserPermissions:
    def test_anon_cannot_list(self, anon_client):
        response = anon_client.get(reverse("user-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_engineer_cannot_list(self, engineer_client):
        response = engineer_client.get(reverse("user-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_cannot_list(self, manager_client):
        response = manager_client.get(reverse("user-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_engineer_cannot_retrieve(self, engineer_client, other_user):
        response = engineer_client.get(reverse("user-detail", args=[other_user.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_retrieve(self, superuser_client, other_user):
        response = superuser_client.get(reverse("user-detail", args=[other_user.pk]))
        assert response.status_code == status.HTTP_200_OK

    def test_write_methods_are_not_allowed(self, superuser_client, other_user):
        assert (
            superuser_client.post(
                reverse("user-list"), {"email": "new@depot.mn"}, format="json"
            ).status_code
            == status.HTTP_405_METHOD_NOT_ALLOWED
        )
        assert (
            superuser_client.patch(
                reverse("user-detail", args=[other_user.pk]),
                {"is_staff": True},
                format="json",
            ).status_code
            == status.HTTP_405_METHOD_NOT_ALLOWED
        )
        assert (
            superuser_client.delete(
                reverse("user-detail", args=[other_user.pk])
            ).status_code
            == status.HTTP_405_METHOD_NOT_ALLOWED
        )
