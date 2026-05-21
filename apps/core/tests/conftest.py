import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker
from rest_framework.test import APIClient

from apps.core.constants import EmployeeRole

User = get_user_model()


@pytest.fixture
def user(db):
    user = User.objects.create_user(
        email="test@depot.mn", password="pass123", is_staff=True
    )
    baker.make("core.Employee", user=user, role=EmployeeRole.ENGINEER)
    return user


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def wagon(db):
    return baker.make("core.Wagon", manufacture_year=2000)


@pytest.fixture
def employee(db):
    return baker.make("core.Employee")
