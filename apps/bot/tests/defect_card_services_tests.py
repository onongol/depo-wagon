"""The defect card query, run against the database."""

import uuid

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from model_bakery import baker

from apps.bot.constants import STATUS_TRANSITIONS
from apps.bot.handlers.tasks.text import build_card_text
from apps.bot.services.defect_card import get_defect_card
from apps.core.constants import EmployeeRole
from apps.defects.constants import DefectStatus

make = sync_to_async(baker.make)

SCOPED_ROLES = [EmployeeRole.INSPECTOR, EmployeeRole.MASTER, EmployeeRole.WORKER]
ALL_ROLES = [EmployeeRole.ENGINEER, EmployeeRole.MANAGER]


async def _defect(**fields):
    wagon = await make("core.Wagon", manufacture_year=2000)
    defaults = {"wagon": wagon, "status": DefectStatus.OPEN}
    return await make("defects.Defect", **(defaults | fields))


async def _employee(role=EmployeeRole.INSPECTOR, **fields):
    return await make("core.Employee", role=role, **fields)


@pytest.mark.django_db(transaction=True)
class TestVisibility:
    @pytest.mark.parametrize("role", SCOPED_ROLES)
    async def test_their_own_defect_opens(self, role):
        mine = await _employee(role)
        defect = await _defect(inspector=mine)

        card = await get_defect_card(defect.pk, employee=mine)

        assert card.defect.pk == defect.pk

    @pytest.mark.parametrize("role", SCOPED_ROLES)
    async def test_someone_elses_does_not(self, role):
        mine = await _employee(role)
        defect = await _defect(inspector=await _employee())

        assert await get_defect_card(defect.pk, employee=mine) is None

    @pytest.mark.parametrize("role", ALL_ROLES)
    async def test_engineers_and_managers_open_any(self, role):
        employee = await _employee(role)
        defect = await _defect(inspector=None)

        assert await get_defect_card(defect.pk, employee=employee) is not None

    async def test_a_closed_defect_still_opens(self):
        mine = await _employee()
        defect = await _defect(inspector=mine, status=DefectStatus.CLOSED)

        assert await get_defect_card(defect.pk, employee=mine) is not None

    async def test_a_missing_defect(self):
        engineer = await _employee(EmployeeRole.ENGINEER)

        assert await get_defect_card(uuid.uuid4(), employee=engineer) is None

    async def test_a_missing_employee_is_refused_rather_than_widened(self):
        defect = await _defect(inspector=None)

        with pytest.raises(ValueError, match="employee"):
            await get_defect_card(defect.pk, employee=None)


@pytest.mark.django_db(transaction=True)
class TestTargets:
    @pytest.mark.parametrize("status", DefectStatus.values)
    async def test_follow_the_transitions(self, status):
        mine = await _employee()
        defect = await _defect(inspector=mine, status=status)

        card = await get_defect_card(defect.pk, employee=mine)

        assert card.targets == STATUS_TRANSITIONS[status]

    async def test_a_closed_defect_offers_nothing(self):
        engineer = await _employee(EmployeeRole.ENGINEER)
        defect = await _defect(status=DefectStatus.CLOSED)

        card = await get_defect_card(defect.pk, employee=engineer)

        assert card.targets == ()

    @pytest.mark.parametrize("role", [EmployeeRole.MASTER, EmployeeRole.WORKER])
    async def test_roles_that_change_no_status_see_the_card_without_any(self, role):
        mine = await _employee(role)
        defect = await _defect(inspector=mine)

        card = await get_defect_card(defect.pk, employee=mine)

        assert card.targets == ()


@pytest.mark.django_db
def test_the_card_text_reads_nothing_the_query_did_not_load(
    django_assert_num_queries,
):
    engineer = baker.make("core.Employee", role=EmployeeRole.ENGINEER)
    defect = baker.make(
        "defects.Defect",
        wagon=baker.make("core.Wagon", manufacture_year=2000),
        inspector=baker.make("core.Employee"),
        responsible_employee=baker.make("core.Employee"),
        status=DefectStatus.OPEN,
    )
    baker.make("defects.DefectMeasurement", defect=defect, _quantity=2)
    baker.make("defects.DefectPhoto", defect=defect, _quantity=3)

    card = async_to_sync(get_defect_card)(defect.pk, employee=engineer)

    assert card.photo_count == 3
    assert len(card.measurements) == 2
    with django_assert_num_queries(0):
        build_card_text(card).render()
