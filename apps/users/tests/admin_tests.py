import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from model_bakery import baker

User = get_user_model()


def _change_page(client, user) -> str:
    url = reverse("admin:users_customuser_change", args=[user.pk])
    return client.get(url).content.decode()


@pytest.mark.django_db
class TestCustomUserAdminActiveFlag:
    """Employee.is_active is the one switch; the bot reads only that one."""

    def test_an_employees_account_cannot_be_switched_here(self, admin_client):
        user = baker.make(User, email="emp@depot.mn")
        baker.make("core.Employee", user=user)

        assert 'name="is_active"' not in _change_page(admin_client, user)

    def test_an_account_without_an_employee_still_can(self, admin_client):
        user = baker.make(User, email="staff@depot.mn")

        assert 'name="is_active"' in _change_page(admin_client, user)
