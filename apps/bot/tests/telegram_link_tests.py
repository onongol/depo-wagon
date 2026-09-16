import threading
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models.signals import pre_save
from model_bakery import baker

from apps.bot.callback_data import CB_LINK_CANCEL, LinkConfirmCB
from apps.bot.constants import LinkStatus
from apps.bot.handlers.common.start import (
    _ATTACH_ERROR_TEXT,
    _RESOLVE_ERROR_TEXT,
    cancel_link,
    confirm_link,
    start,
    start_with_link,
)
from apps.bot.services.employee import get_employee_by_telegram_id
from apps.bot.services.telegram_link import (
    attach_telegram,
    claim_pending_link,
    forget_pending_link,
    remember_pending_link,
    resolve_link_token,
)
from apps.bot.tests.builders import make_callback, make_command, make_message
from apps.users import telegram_tokens

make = sync_to_async(baker.make)
User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield


def _claim_the_chat(telegram_id):
    """Take the chat the way another process would: own connection, own commit."""
    try:
        baker.make("core.Employee", telegram_id=telegram_id, is_active=True)
    finally:
        connection.close()


@contextmanager
def rival_claims_the_chat(telegram_id):
    """Let a rival take the chat between attach_telegram's check and its save."""
    from apps.core.models import Employee

    def on_save(sender, instance, **kwargs):
        pre_save.disconnect(on_save, sender=Employee)
        rival = threading.Thread(target=_claim_the_chat, args=(telegram_id,))
        rival.start()
        rival.join()

    pre_save.connect(on_save, sender=Employee)
    try:
        yield
    finally:
        pre_save.disconnect(on_save, sender=Employee)


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

    def test_a_chat_claimed_between_the_check_and_the_save_is_refused(self):
        from apps.core.models import Employee

        employee = baker.make("core.Employee", telegram_id=None, is_active=True)

        with rival_claims_the_chat(777):
            _, status = async_to_sync(attach_telegram)(employee.pk, telegram_id=777)

        assert status is LinkStatus.ALREADY_LINKED
        assert Employee.objects.get(pk=employee.pk).telegram_id is None

    def test_a_lost_race_leaves_the_outer_transaction_usable(self):
        """The savepoint, not just the except: callers may be mid-transaction."""
        from apps.core.models import Employee

        employee = baker.make("core.Employee", telegram_id=None, is_active=True)

        with transaction.atomic():
            with rival_claims_the_chat(777):
                _, status = async_to_sync(attach_telegram)(employee.pk, telegram_id=777)
            assert Employee.objects.filter(pk=employee.pk).exists()

        assert status is LinkStatus.ALREADY_LINKED

    async def test_deactivation_between_question_and_answer_is_refused(self):
        employee = await make("core.Employee", telegram_id=None, is_active=True)
        employee.is_active = False
        await sync_to_async(employee.save)(update_fields=["is_active"])

        _, status = await attach_telegram(employee.pk, telegram_id=777)

        assert status is LinkStatus.NO_EMPLOYEE


class TestPendingLink:
    async def test_the_offer_is_single_use(self):
        await remember_pending_link(777, 42)

        assert await claim_pending_link(777, 42) is True
        assert await claim_pending_link(777, 42) is False

    async def test_an_offer_naming_another_employee_is_refused(self):
        await remember_pending_link(777, 42)

        assert await claim_pending_link(777, 43) is False

    async def test_a_refused_claim_leaves_the_offer_standing(self):
        await remember_pending_link(777, 42)
        await claim_pending_link(777, 43)

        assert await claim_pending_link(777, 42) is True

    async def test_a_new_offer_replaces_the_one_before_it(self):
        await remember_pending_link(777, 42)
        await remember_pending_link(777, 43)

        assert await claim_pending_link(777, 42) is False
        assert await claim_pending_link(777, 43) is True

    async def test_one_chat_cannot_claim_another_chats_offer(self):
        await remember_pending_link(777, 42)

        assert await claim_pending_link(778, 42) is False

    async def test_a_dropped_offer_is_gone(self):
        await remember_pending_link(777, 42)
        await forget_pending_link(777)

        assert await claim_pending_link(777, 42) is False


@pytest.mark.django_db(transaction=True)
class TestEmployeeIsReadFresh:
    """What the web revokes, the bot must stop honouring on the next update."""

    async def test_disconnecting_reaches_the_bot(self):
        employee = await make("core.Employee", telegram_id=777, is_active=True)
        assert await get_employee_by_telegram_id(777) is not None

        employee.telegram_id = None
        await sync_to_async(employee.save)(update_fields=["telegram_id"])

        assert await get_employee_by_telegram_id(777) is None

    async def test_deactivation_reaches_the_bot(self):
        employee = await make("core.Employee", telegram_id=777, is_active=True)
        assert await get_employee_by_telegram_id(777) is not None

        employee.is_active = False
        await sync_to_async(employee.save)(update_fields=["is_active"])

        assert await get_employee_by_telegram_id(777) is None


class TestStartHandler:
    async def test_bare_start_when_unlinked_points_at_the_web_app(self):
        message = make_message()
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.get_connect_url = MagicMock(return_value="https://x/telegram/")
            await start(message, None)
        assert "https://x/telegram/" in message.answer.await_args.args[0]

    async def test_bare_start_when_linked_shows_menu(self):
        message = make_message()
        employee = MagicMock()
        with patch(
            "apps.bot.handlers.common.start.show_welcome_menu",
            new_callable=AsyncMock,
        ) as menu:
            await start(message, employee)
        menu.assert_awaited_once()

    async def test_token_is_passed_through_to_the_service(self):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                return_value=(_make_employee_mock(), LinkStatus.OK)
            )
            svc.remember_pending_link = AsyncMock()
            await start_with_link(message, command)
        assert svc.resolve_link_token.await_args.args[0] == "sometoken"

    async def test_token_offers_the_employee_it_resolved(self):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                return_value=(_make_employee_mock(pk=42), LinkStatus.OK)
            )
            svc.remember_pending_link = AsyncMock()
            await start_with_link(message, command)

        kwargs = message.answer.await_args.kwargs
        button = kwargs["reply_markup"].inline_keyboard[0][0]
        assert LinkConfirmCB.unpack(button.callback_data).employee_id == 42

    async def test_the_offer_is_recorded_against_this_chat(self):
        message = make_message(user_id=777)
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                return_value=(_make_employee_mock(pk=42), LinkStatus.OK)
            )
            svc.remember_pending_link = AsyncMock()
            await start_with_link(message, command)
        assert svc.remember_pending_link.await_args.args == (777, 42)

    async def test_no_offer_is_recorded_without_a_button(self):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                return_value=(None, LinkStatus.INVALID_TOKEN)
            )
            svc.remember_pending_link = AsyncMock()
            await start_with_link(message, command)
        svc.remember_pending_link.assert_not_awaited()

    async def test_an_unrecordable_offer_shows_no_button(self):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                return_value=(_make_employee_mock(), LinkStatus.OK)
            )
            svc.remember_pending_link = AsyncMock(side_effect=Exception("redis down"))
            await start_with_link(message, command)
        assert "reply_markup" not in message.answer.await_args.kwargs

    async def test_token_attaches_nothing_on_its_own(self):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(
                return_value=(_make_employee_mock(), LinkStatus.OK)
            )
            svc.remember_pending_link = AsyncMock()
            await start_with_link(message, command)
        svc.attach_telegram.assert_not_called()

    @pytest.mark.parametrize("status", sorted(_RESOLVE_ERROR_TEXT))
    async def test_unresolvable_token_offers_nothing(self, status):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(return_value=(None, status))
            await start_with_link(message, command)
        assert "reply_markup" not in message.answer.await_args.kwargs

    async def test_service_failure_is_reported_not_raised(self):
        message = make_message()
        command = make_command("sometoken")
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.resolve_link_token = AsyncMock(side_effect=Exception("redis down"))
            await start_with_link(message, command)
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
            svc.claim_pending_link = AsyncMock(return_value=True)
            svc.attach_telegram = AsyncMock(return_value=(MagicMock(), LinkStatus.OK))
            await confirm_link(callback, callback_data)
        assert svc.claim_pending_link.await_args.args == (777, 42)
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
            svc.claim_pending_link = AsyncMock(return_value=True)
            svc.attach_telegram = AsyncMock(return_value=(employee, LinkStatus.OK))
            await confirm_link(callback, callback_data)
        assert menu.await_args.args[1] is employee

    @pytest.mark.parametrize("status", sorted(_ATTACH_ERROR_TEXT))
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
            svc.claim_pending_link = AsyncMock(return_value=True)
            svc.attach_telegram = AsyncMock(return_value=(None, status))
            await confirm_link(callback, callback_data)
        menu.assert_not_awaited()

    async def test_service_failure_is_reported_not_raised(self):
        callback = make_callback(user_id=12345)
        callback_data = LinkConfirmCB(employee_id=42)
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.claim_pending_link = AsyncMock(return_value=True)
            svc.attach_telegram = AsyncMock(side_effect=Exception("db down"))
            await confirm_link(callback, callback_data)
        callback.message.edit_text.assert_awaited_once()

    async def test_an_unclaimed_offer_attaches_nothing(self):
        callback = make_callback(user_id=12345)
        callback_data = LinkConfirmCB(employee_id=42)
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.claim_pending_link = AsyncMock(return_value=False)
            await confirm_link(callback, callback_data)
        svc.attach_telegram.assert_not_called()
        callback.message.edit_text.assert_awaited_once()

    async def test_an_unreadable_offer_attaches_nothing(self):
        callback = make_callback(user_id=12345)
        callback_data = LinkConfirmCB(employee_id=42)
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.claim_pending_link = AsyncMock(side_effect=Exception("redis down"))
            await confirm_link(callback, callback_data)
        svc.attach_telegram.assert_not_called()
        callback.message.edit_text.assert_awaited_once()


class TestLinkStatusRouting:
    def test_every_failure_status_reaches_a_message(self):
        routed = _RESOLVE_ERROR_TEXT.keys() | _ATTACH_ERROR_TEXT.keys()
        assert routed == set(LinkStatus) - {LinkStatus.OK}

    async def test_an_unrouted_status_still_answers(self, caplog):
        callback = make_callback(user_id=12345)
        callback_data = LinkConfirmCB(employee_id=42)
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.claim_pending_link = AsyncMock(return_value=True)
            svc.attach_telegram = AsyncMock(
                return_value=(None, LinkStatus.INVALID_TOKEN)
            )
            await confirm_link(callback, callback_data)
        callback.message.edit_text.assert_awaited_once()
        assert "no message on this path" in caplog.text


@pytest.mark.django_db(transaction=True)
class TestForwardedDeepLink:
    """The button in a chat that was never meant to have it."""

    async def _offer_to(self, telegram_id: int):
        user = await make("users.CustomUser")
        employee = await make(
            "core.Employee", user=user, telegram_id=None, is_active=True
        )
        token = await sync_to_async(telegram_tokens.issue)(user.pk)
        await start_with_link(make_message(user_id=telegram_id), make_command(token))
        return employee

    async def test_the_chat_that_followed_the_link_can_confirm(self):
        employee = await self._offer_to(999)

        with patch("apps.users.notifications.notify_telegram_link_change"):
            await confirm_link(
                make_callback(user_id=999), LinkConfirmCB(employee_id=employee.pk)
            )

        await sync_to_async(employee.refresh_from_db)()
        assert employee.telegram_id == 999

    async def test_a_button_outliving_its_offer_attaches_nothing(self):
        employee = await self._offer_to(999)
        await forget_pending_link(999)

        await confirm_link(
            make_callback(user_id=999), LinkConfirmCB(employee_id=employee.pk)
        )

        await sync_to_async(employee.refresh_from_db)()
        assert employee.telegram_id is None

    async def test_a_stale_button_cannot_move_a_chat_already_linked(self):
        employee = await self._offer_to(999)
        await forget_pending_link(999)
        employee.telegram_id = 777
        await sync_to_async(employee.save)(update_fields=["telegram_id"])

        await confirm_link(
            make_callback(user_id=999), LinkConfirmCB(employee_id=employee.pk)
        )

        await sync_to_async(employee.refresh_from_db)()
        assert employee.telegram_id == 777

    async def test_the_button_works_once(self):
        employee = await self._offer_to(999)
        callback_data = LinkConfirmCB(employee_id=employee.pk)

        with patch("apps.users.notifications.notify_telegram_link_change") as notify:
            await confirm_link(make_callback(user_id=999), callback_data)
            await confirm_link(make_callback(user_id=999), callback_data)

        notify.assert_called_once()


class TestCancelLink:
    async def test_attaches_nothing(self):
        callback = make_callback(CB_LINK_CANCEL)
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.forget_pending_link = AsyncMock()
            await cancel_link(callback)
        svc.attach_telegram.assert_not_called()

    async def test_says_so(self):
        callback = make_callback(CB_LINK_CANCEL)
        await cancel_link(callback)
        callback.message.edit_text.assert_awaited_once()

    async def test_drops_the_offer(self):
        callback = make_callback(CB_LINK_CANCEL, user_id=777)
        await remember_pending_link(777, 42)

        await cancel_link(callback)

        assert await claim_pending_link(777, 42) is False
