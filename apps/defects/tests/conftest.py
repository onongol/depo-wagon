import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_superuser(email="test@depot.mn", password="pass123")


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


@pytest.fixture
def defect(db, wagon, employee):
    return baker.make("defects.Defect", wagon=wagon, inspector=employee)
