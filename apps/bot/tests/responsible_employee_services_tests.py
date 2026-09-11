"""The responsible-employee queries, run against the database."""

import pytest
from asgiref.sync import sync_to_async
from model_bakery import baker

from apps.bot.services.responsible_employee import (
    count_department_employees,
    get_department_employee,
    get_department_employees,
)
from apps.core.constants import Department

make = sync_to_async(baker.make)


async def _employee(**fields):
    defaults = {"department": Department.BOGIE, "is_active": True}
    return await make("core.Employee", **(defaults | fields))


@pytest.mark.django_db(transaction=True)
class TestDepartmentEmployees:
    async def test_counts_only_active_employees_of_that_department(self):
        await _employee()
        await _employee(is_active=False)
        await _employee(department=Department.WHEELSET)

        assert await count_department_employees(Department.BOGIE) == 1

    async def test_an_unset_department_matches_nobody(self):
        await _employee(department="")

        assert await count_department_employees("") == 0
        assert await count_department_employees(None) == 0

    async def test_search_runs_across_first_and_last_name(self):
        await _employee(first_name="Бат", last_name="Эрдэнэ")
        await _employee(first_name="Болд", last_name="Сүх")

        assert await count_department_employees(Department.BOGIE, "т эр") == 1

    async def test_search_ignores_case_in_cyrillic(self):
        await _employee(first_name="Өлзий", last_name="Бат")

        assert await count_department_employees(Department.BOGIE, "өЛЗ") == 1

    async def test_search_treats_wildcards_literally(self):
        await _employee(first_name="Бат")

        assert await count_department_employees(Department.BOGIE, "%") == 0

    async def test_a_page_is_ordered_by_last_then_first_name(self):
        await _employee(first_name="Б", last_name="Я")
        await _employee(first_name="В", last_name="А")
        await _employee(first_name="А", last_name="А")

        page = await get_department_employees(Department.BOGIE, limit=5)

        assert [(e.last_name, e.first_name) for e in page] == [
            ("А", "А"),
            ("А", "В"),
            ("Я", "Б"),
        ]

    async def test_limit_and_offset_cut_one_page(self):
        for i in range(7):
            await _employee(first_name=f"N{i}", last_name=f"L{i}")

        page = await get_department_employees(Department.BOGIE, limit=5, offset=5)

        assert [e.last_name for e in page] == ["L5", "L6"]

    async def test_the_chosen_employee_is_returned_while_eligible(self):
        employee = await _employee()

        chosen = await get_department_employee(employee.pk, Department.BOGIE)

        assert chosen.pk == employee.pk

    async def test_the_chosen_employee_is_refused_once_deactivated(self):
        employee = await _employee(is_active=False)

        assert await get_department_employee(employee.pk, Department.BOGIE) is None

    async def test_the_chosen_employee_is_refused_from_another_department(self):
        employee = await _employee(department=Department.WHEELSET)

        assert await get_department_employee(employee.pk, Department.BOGIE) is None
