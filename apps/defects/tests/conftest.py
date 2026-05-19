import pytest
from model_bakery import baker


@pytest.fixture
def wagon():
    return baker.make("core.Wagon", manufacture_year=2000)


@pytest.fixture
def employee():
    return baker.make("core.Employee")


@pytest.fixture
def defect(wagon, employee):
    return baker.make("defects.Defect", wagon=wagon, inspector=employee)
