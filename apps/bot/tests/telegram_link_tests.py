from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import cache
from model_bakery import baker

from apps.bot.callback_data import CB_LINK_CANCEL, LinkConfirmCB
from apps.bot.constants import LinkStatus
from apps.bot.handlers.common.start import cancel_link, confirm_link, start
from apps.bot.handlers.employee import get_employee
from apps.bot.services.telegram_link import attach_telegram, resolve_link_token
from apps.bot.tests.builders import make_callback, make_command, make_message
from apps.users import telegram_tokens

make = sync_to_async(baker.make)
User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield


def _make_employee_mock(pk=7, full_name="Batbayar Bat"):
    employee = MagicMock()
    employee.pk = pk
    employee.full_name = full_name
    return employee


@pytest.mark.django_db(transaction=True)
class TestResolveLinkToken:
    async def test_valid_token_returns_the_employee(self):
        user = await make("users.CustomUser")
        await make("core.Employee", user=user, telegram_id=None, is_active=True)
        token = await sync_to_async(telegram_tokens.issue)(user.pk)

        employee, status = await resolve_link_token(token)

        assert status is LinkStatus.OK
        assert employee.user_id == user.pk

    async def test_resolving_attaches_nothing(self):
        user = await make("users.CustomUser")
        await make("core.Employee", user=user, telegram_id=None, is_active=True)
        token = await sync_to_async(telegram_tokens.issue)(user.pk)

        employee, _ = await resolve_link_token(token)

        assert employee.telegram_id is None

    async def test_token_works_only_once(self):
        user = await make("users.CustomUser")
        await make("core.Employee", user=user, telegram_id=None, is_active=True)
        token = await sync_to_async(telegram_tokens.issue)(user.pk)

        await resolve_link_token(token)
        _, status = await resolve_link_token(token)

        assert status is LinkStatus.INVALID_TOKEN

    async def test_unknown_token_is_rejected(self):
        _, status = await resolve_link_token("never-issued")
        assert status is LinkStatus.INVALID_TOKEN

    async def test_user_without_employee_is_rejected(self):
        user = await make("users.CustomUser")
        token = await sync_to_async(telegram_tokens.issue)(user.pk)

        _, status = await resolve_link_token(token)

        assert status is LinkStatus.NO_EMPLOYEE


@pytest.mark.django_db(transaction=True)
class TestAttachTelegram:
    async def test_records_the_chat(self):
        employee = await make("core.Employee", telegram_id=None, is_active=True)

        attached, status = await attach_telegram(employee.pk, telegram_id=777)

        assert status is LinkStatus.OK
        assert attached.telegram_id == 777

    async def test_chat_already_owned_by_someone_else_is_rejected(self):
        await make("core.Employee", telegram_id=777, is_active=True)
        employee = await make("core.Employee", telegram_id=None, is_active=True)

        _, status = await attach_telegram(employee.pk, telegram_id=777)

        assert status is LinkStatus.ALREADY_LINKED

    async def test_chat_owned_by_an_inactive_employee_is_rejected(self):
        await make("core.Employee", telegram_id=777, is_active=False)
        employee = await make("core.Employee", telegram_id=None, is_active=True)

        _, status = await attach_telegram(employee.pk, telegram_id=777)

        assert status is LinkStatus.ALREADY_LINKED

    async def test_relinking_the_same_chat_is_allowed(self):
        employee = await make("core.Employee", telegram_id=777, is_active=True)

        _, status = await attach_telegram(employee.pk, telegram_id=777)

        assert status is LinkStatus.OK

    async def test_the_owner_is_notified(self):
        user = await make("users.CustomUser")
        employee = await make(
            "core.Employee", user=user, telegram_id=None, is_active=True
        )

        with patch("apps.users.notifications.notify_telegram_link_change") as notify:
            await attach_telegram(employee.pk, telegram_id=777)

        notify.assert_called_once_with(user, "connected")

    async def test_an_employee_without_an_account_notifies_nobody(self):
        employee = await make("core.Employee", telegram_id=None, is_active=True)

        with patch("apps.users.notifications.notify_telegram_link_change") as notify:
            await attach_telegram(employee.pk, telegram_id=777)

        notify.assert_not_called()

    async def test_deactivation_between_question_and_answer_is_refused(self):
        employee = await make("core.Employee", telegram_id=None, is_active=True)
        employee.is_active = False
        await sync_to_async(employee.save)(update_fields=["is_active"])

        _, status = await attach_telegram(employee.pk, telegram_id=777)

        assert status is LinkStatus.NO_EMPLOYEE


@pytest.mark.django_db(transaction=True)
class TestEmployeeIsReadFresh:
    """What the web revokes, the bot must stop honouring on the next update."""

    async def test_disconnecting_reaches_the_bot(self):
        employee = await make("core.Employee", telegram_id=777, is_active=True)
        assert await get_employee(777) is not None

        employee.telegram_id = None
        await sync_to_async(employee.save)(update_fields=["telegram_id"])

        assert await get_employee(777) is None

    async def test_deactivation_reaches_the_bot(self):
        employee = await make("core.Employee", telegram_id=777, is_active=True)
        assert await get_employee(777) is not None

        employee.is_active = False
        await sync_to_async(employee.save)(update_fields=["is_active"])

        assert await get_employee(777) is None


class TestStartHandler:
    async def test_bare_start_when_unlinked_points_at_the_web_app(self):
        message = make_message()
        command = make_command()
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.get_employee_by_telegram_id = AsyncMock(return_value=None)
            svc.get_connect_url = MagicMock(return_value="https://x/telegram/")
            await start(message, command)
        assert "https://x/telegram/" in message.answer.await_args.args[0]

    async def test_bare_start_when_linked_shows_menu(self):
        message = make_message()
        command = make_command()
        employee = MagicMock()
        with (
            patch("apps.bot.handlers.common.start.services") as svc,
            patch(
                "apps.bot.handlers.common.start.show_welcome_menu",
                new_callable=AsyncMock,
            ) as menu,
        ):
            svc.get_employee_by_telegram_id = AsyncMock(return_value=employee)
            await start(message, command)
        menu.assert_awaited_once()

    async def test_token_is_passed_through_to_the_service(self):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                return_value=(_make_employee_mock(), LinkStatus.OK)
            )
            await start(message, command)
        assert svc.resolve_link_token.await_args.args[0] == "sometoken"

    async def test_token_offers_the_employee_it_resolved(self):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                return_value=(_make_employee_mock(pk=42), LinkStatus.OK)
            )
            await start(message, command)

        kwargs = message.answer.await_args.kwargs
        button = kwargs["reply_markup"].inline_keyboard[0][0]
        assert LinkConfirmCB.unpack(button.callback_data).employee_id == 42

    async def test_token_attaches_nothing_on_its_own(self):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                return_value=(_make_employee_mock(), LinkStatus.OK)
            )
            await start(message, command)
        svc.attach_telegram.assert_not_called()

    @pytest.mark.parametrize(
        "status",
        [LinkStatus.INVALID_TOKEN, LinkStatus.NO_EMPLOYEE],
    )
    async def test_unresolvable_token_offers_nothing(self, status):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(return_value=(None, status))
            await start(message, command)
        assert "reply_markup" not in message.answer.await_args.kwargs

    async def test_service_failure_is_reported_not_raised(self):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(side_effect=Exception("redis down"))
            await start(message, command)
        message.answer.assert_awaited_once()


class TestConfirmLink:
    async def test_attaches_the_offered_employee_to_this_chat(self):
        callback = make_callback(user_id=777)
        callback_data = LinkConfirmCB(employee_id=42)
        with (
            patch("apps.bot.handlers.common.start.services") as svc,
            patch(
                "apps.bot.handlers.common.start.show_welcome_menu",
                new_callable=AsyncMock,
            ),
        ):
            svc.attach_telegram = AsyncMock(return_value=(MagicMock(), LinkStatus.OK))
            await confirm_link(callback, callback_data)
        assert svc.attach_telegram.await_args.args == (42, 777)

    async def test_shows_the_menu_for_the_employee_attached(self):
        callback = make_callback(user_id=12345)
        callback_data = LinkConfirmCB(employee_id=42)
        employee = MagicMock()
        with (
            patch("apps.bot.handlers.common.start.services") as svc,
            patch(
                "apps.bot.handlers.common.start.show_welcome_menu",
                new_callable=AsyncMock,
            ) as menu,
        ):
            svc.attach_telegram = AsyncMock(return_value=(employee, LinkStatus.OK))
            await confirm_link(callback, callback_data)
        assert menu.await_args.args[1] is employee

    @pytest.mark.parametrize(
        "status",
        [LinkStatus.NO_EMPLOYEE, LinkStatus.ALREADY_LINKED],
    )
    async def test_failed_attach_shows_no_menu(self, status):
        callback = make_callback(user_id=12345)
        callback_data = LinkConfirmCB(employee_id=42)
        with (
            patch("apps.bot.handlers.common.start.services") as svc,
            patch(
                "apps.bot.handlers.common.start.show_welcome_menu",
                new_callable=AsyncMock,
            ) as menu,
        ):
            svc.attach_telegram = AsyncMock(return_value=(None, status))
            await confirm_link(callback, callback_data)
        menu.assert_not_awaited()

    async def test_service_failure_is_reported_not_raised(self):
        callback = make_callback(user_id=12345)
        callback_data = LinkConfirmCB(employee_id=42)
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.attach_telegram = AsyncMock(side_effect=Exception("db down"))
            await confirm_link(callback, callback_data)
        callback.message.edit_text.assert_awaited_once()


class TestCancelLink:
    async def test_attaches_nothing(self):
        callback = make_callback(CB_LINK_CANCEL)
        with patch("apps.bot.handlers.common.start.services") as svc:
            await cancel_link(callback)
        svc.attach_telegram.assert_not_called()

    async def test_says_so(self):
        callback = make_callback(CB_LINK_CANCEL)
        await cancel_link(callback)
        callback.message.edit_text.assert_awaited_once()
