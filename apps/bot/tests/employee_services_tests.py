"""The employee queries, run against the database."""

import pytest
from asgiref.sync import sync_to_async
from model_bakery import baker

from apps.bot.services.employee import get_employee_by_telegram_id
from apps.core.constants import Department

make = sync_to_async(baker.make)


async def _employee(**fields):
    defaults = {"department": Department.BOGIE, "is_active": True}
    return await make("core.Employee", **(defaults | fields))


@pytest.mark.django_db(transaction=True)
class TestGetEmployeeByTelegramId:
    async def test_returns_the_active_employee_on_that_chat(self):
        employee = await _employee(telegram_id=111)

        assert (await get_employee_by_telegram_id(111)).pk == employee.pk

    async def test_a_deactivated_employee_is_not_returned(self):
        await _employee(telegram_id=111, is_active=False)

        assert await get_employee_by_telegram_id(111) is None

    async def test_an_unknown_chat_returns_none(self):
        assert await get_employee_by_telegram_id(111) is None
