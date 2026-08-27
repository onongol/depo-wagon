import pytest
from asgiref.sync import sync_to_async
from django.core.cache import cache
from model_bakery import baker

from apps.bot.services.employee import link_employee_telegram

make = sync_to_async(baker.make)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield


@pytest.mark.django_db(transaction=True)
class TestLinkEmployeeTelegram:
    async def test_successful_link(self):
        await make("core.Employee", employee_id="001", telegram_id=None)

        result, status = await link_employee_telegram("001", telegram_id=55555)

        assert status == "ok"
        assert result is not None
        assert result.telegram_id == 55555

    async def test_employee_not_found(self):
        result, status = await link_employee_telegram("NONEXISTENT", telegram_id=55555)

        assert status == "not_found"
        assert result is None

    async def test_already_linked_to_different_account(self):
        await make("core.Employee", employee_id="002", telegram_id=99999)

        result, status = await link_employee_telegram("002", telegram_id=11111)

        assert status == "already_linked"
        assert result is None

    async def test_same_telegram_id_allows_relink(self):
        await make("core.Employee", employee_id="003", telegram_id=55555)

        result, status = await link_employee_telegram("003", telegram_id=55555)

        assert status == "ok"
        assert result is not None
