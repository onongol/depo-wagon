import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from model_bakery import baker
from rest_framework.test import APIClient

from apps.core.constants import EmployeeRole

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_cache():
    """Sign-in rate limits are counted in the cache; don't leak them between tests."""
    cache.clear()
    yield
    cache.clear()


def make_client_with_role(role):
    user = User.objects.create_user(email=f"{role}@depot.mn", password="pass123")
    employee = baker.make("core.Employee", user=user, role=role)
    client = APIClient()
    client.force_authenticate(user=user)
    client.employee = employee
    return client


@pytest.fixture
def inspector_client(db):
    return make_client_with_role(EmployeeRole.INSPECTOR)


@pytest.fixture
def engineer_client(db):
    return make_client_with_role(EmployeeRole.ENGINEER)


@pytest.fixture
def manager_client(db):
    return make_client_with_role(EmployeeRole.MANAGER)


@pytest.fixture
def master_client(db):
    return make_client_with_role(EmployeeRole.MASTER)


@pytest.fixture
def superuser_client(db):
    user = User.objects.create_superuser(email="admin@depot.mn", password="pass123")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def no_employee_client(db):
    user = User.objects.create_user(email="noemployee@depot.mn", password="pass123")
    client = APIClient()
    client.force_authenticate(user=user)
    return client
