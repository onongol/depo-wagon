import pytest
from asgiref.sync import sync_to_async
from django.core.cache import cache
from model_bakery import baker

from apps.bot.constants import OtpStatus, RegStatus
from apps.bot.services.employee import link_employee_telegram, register_employee
from apps.bot.services.otp import generate_and_store_otp, verify_otp

make = sync_to_async(baker.make)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield


class TestVerifyOtp:
    async def test_correct_code_returns_ok(self):
        code = await generate_and_store_otp("user@depot.mn", employee_id=42)
        employee_id, status = await verify_otp("user@depot.mn", code)
        assert status == OtpStatus.OK
        assert employee_id == 42

    async def test_wrong_code_returns_wrong(self):
        await generate_and_store_otp("user@depot.mn", employee_id=42)
        employee_id, status = await verify_otp("user@depot.mn", "000000")
        assert status == OtpStatus.WRONG
        assert employee_id is None

    async def test_wrong_code_increments_attempts(self):
        await generate_and_store_otp("user@depot.mn", employee_id=42)
        await verify_otp("user@depot.mn", "000000")  # attempt 1
        await verify_otp("user@depot.mn", "000000")  # attempt 2
        _, status = await verify_otp("user@depot.mn", "000000")  # attempt 3 → max
        assert status == OtpStatus.MAX_ATTEMPTS

    async def test_max_attempts_invalidates_otp(self):
        await generate_and_store_otp("user@depot.mn", employee_id=42)
        for _ in range(3):
            await verify_otp("user@depot.mn", "000000")
        _, status = await verify_otp("user@depot.mn", "000000")  # 4th → expired
        assert status == OtpStatus.EXPIRED

    async def test_expired_otp_returns_expired(self):
        _, status = await verify_otp("nokey@depot.mn", "123456")
        assert status == OtpStatus.EXPIRED

    async def test_correct_code_consumed_on_use(self):
        code = await generate_and_store_otp("user@depot.mn", employee_id=42)
        await verify_otp("user@depot.mn", code)
        _, status = await verify_otp("user@depot.mn", code)
        assert status == OtpStatus.EXPIRED

    async def test_email_lookup_is_case_insensitive(self):
        code = await generate_and_store_otp("USER@DEPOT.MN", employee_id=42)
        _, status = await verify_otp("user@depot.mn", code)
        assert status == OtpStatus.OK


@pytest.mark.django_db(transaction=True)
class TestRegisterEmployee:
    async def test_existing_user_links_telegram_id(self):
        user = await make("users.CustomUser")
        employee = await make("core.Employee", user=user, telegram_id=None)

        _, status = await register_employee(employee, telegram_id=11111)

        assert status == RegStatus.LINKED
        assert employee.telegram_id == 11111

    async def test_existing_user_returns_no_password(self):
        user = await make("users.CustomUser")
        employee = await make("core.Employee", user=user, telegram_id=None)

        password, _ = await register_employee(employee, telegram_id=11111)

        assert password is None

    async def test_no_user_creates_custom_user(self):
        employee = await make(
            "core.Employee",
            user=None,
            email="new@depot.mn",
            first_name="Бат",
            last_name="Дорж",
        )

        await register_employee(employee, telegram_id=22222)

        assert employee.user_id is not None

    async def test_no_user_returns_created_status(self):
        employee = await make(
            "core.Employee",
            user=None,
            email="new@depot.mn",
            first_name="Бат",
            last_name="Дорж",
        )

        _, status = await register_employee(employee, telegram_id=22222)

        assert status == RegStatus.CREATED

    async def test_no_user_returns_generated_password(self):
        employee = await make(
            "core.Employee",
            user=None,
            email="new@depot.mn",
            first_name="Бат",
            last_name="Дорж",
        )

        password, _ = await register_employee(employee, telegram_id=22222)

        assert password is not None
        assert len(password) == 12

    async def test_duplicate_email_returns_already_exists(self):
        await make("users.CustomUser", email="dup@depot.mn")
        employee = await make("core.Employee", user=None, email="dup@depot.mn")

        _, status = await register_employee(employee, telegram_id=33333)

        assert status == RegStatus.ALREADY_EXISTS


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
