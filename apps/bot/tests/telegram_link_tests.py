from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import cache
from model_bakery import baker

from apps.bot.constants import UD_EMPLOYEE, LinkStatus
from apps.bot.handlers.common.start import start
from apps.bot.services.telegram_link import link_telegram_by_token
from apps.users import telegram_tokens

make = sync_to_async(baker.make)
User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield


def _make_update(user_id=12345):
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    update.effective_user.id = user_id
    return update


@pytest.mark.django_db(transaction=True)
class TestLinkTelegramByToken:
    async def test_valid_token_links_the_chat(self):
        user = await make("users.CustomUser")
        await make("core.Employee", user=user, telegram_id=None, is_active=True)
        token = await sync_to_async(telegram_tokens.issue)(user.pk)

        employee, status = await link_telegram_by_token(token, telegram_id=777)

        assert status is LinkStatus.OK
        assert employee.telegram_id == 777

    async def test_token_works_only_once(self):
        user = await make("users.CustomUser")
        await make("core.Employee", user=user, telegram_id=None, is_active=True)
        token = await sync_to_async(telegram_tokens.issue)(user.pk)

        await link_telegram_by_token(token, telegram_id=777)
        _, status = await link_telegram_by_token(token, telegram_id=888)

        assert status is LinkStatus.INVALID_TOKEN

    async def test_unknown_token_is_rejected(self):
        _, status = await link_telegram_by_token("never-issued", telegram_id=777)
        assert status is LinkStatus.INVALID_TOKEN

    async def test_user_without_employee_is_rejected(self):
        user = await make("users.CustomUser")
        token = await sync_to_async(telegram_tokens.issue)(user.pk)

        _, status = await link_telegram_by_token(token, telegram_id=777)

        assert status is LinkStatus.NO_EMPLOYEE

    async def test_chat_already_owned_by_someone_else_is_rejected(self):
        await make("core.Employee", telegram_id=777, is_active=True)
        user = await make("users.CustomUser")
        await make("core.Employee", user=user, telegram_id=None, is_active=True)
        token = await sync_to_async(telegram_tokens.issue)(user.pk)

        _, status = await link_telegram_by_token(token, telegram_id=777)

        assert status is LinkStatus.ALREADY_LINKED

    async def test_relinking_the_same_chat_is_allowed(self):
        user = await make("users.CustomUser")
        await make("core.Employee", user=user, telegram_id=777, is_active=True)
        token = await sync_to_async(telegram_tokens.issue)(user.pk)

        _, status = await link_telegram_by_token(token, telegram_id=777)

        assert status is LinkStatus.OK


class TestStartHandler:
    async def test_bare_start_when_unlinked_points_at_the_web_app(self, mock_context):
        update = _make_update()
        mock_context.args = []
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.get_employee_by_telegram_id = AsyncMock(return_value=None)
            svc.get_connect_url = MagicMock(return_value="https://x/telegram/")
            await start(update, mock_context)
        assert "https://x/telegram/" in update.message.reply_text.await_args.args[0]

    async def test_bare_start_when_linked_shows_menu(self, mock_context):
        update = _make_update()
        mock_context.args = []
        employee = MagicMock()
        with (
            patch("apps.bot.handlers.common.start.services") as svc,
            patch(
                "apps.bot.handlers.common.start.show_welcome_menu",
                new_callable=AsyncMock,
            ) as menu,
        ):
            svc.get_employee_by_telegram_id = AsyncMock(return_value=employee)
            await start(update, mock_context)
        menu.assert_awaited_once()

    async def test_token_links_and_caches_the_employee(self, mock_context):
        update = _make_update()
        mock_context.args = ["sometoken"]
        employee = MagicMock()
        with (
            patch("apps.bot.handlers.common.start.services") as svc,
            patch(
                "apps.bot.handlers.common.start.show_welcome_menu",
                new_callable=AsyncMock,
            ),
        ):
            svc.link_telegram_by_token = AsyncMock(
                return_value=(employee, LinkStatus.OK)
            )
            await start(update, mock_context)
        assert mock_context.user_data[UD_EMPLOYEE] is employee

    async def test_token_is_passed_through_to_the_service(self, mock_context):
        update = _make_update()
        mock_context.args = ["sometoken"]
        with (
            patch("apps.bot.handlers.common.start.services") as svc,
            patch(
                "apps.bot.handlers.common.start.show_welcome_menu",
                new_callable=AsyncMock,
            ),
        ):
            svc.link_telegram_by_token = AsyncMock(
                return_value=(MagicMock(), LinkStatus.OK)
            )
            await start(update, mock_context)
        assert svc.link_telegram_by_token.await_args.args[0] == "sometoken"

    @pytest.mark.parametrize(
        "status",
        [
            LinkStatus.INVALID_TOKEN,
            LinkStatus.NO_EMPLOYEE,
            LinkStatus.ALREADY_LINKED,
        ],
    )
    async def test_failed_link_shows_no_menu(self, mock_context, status):
        update = _make_update()
        mock_context.args = ["sometoken"]
        with (
            patch("apps.bot.handlers.common.start.services") as svc,
            patch(
                "apps.bot.handlers.common.start.show_welcome_menu",
                new_callable=AsyncMock,
            ) as menu,
        ):
            svc.link_telegram_by_token = AsyncMock(return_value=(None, status))
            await start(update, mock_context)
        menu.assert_not_awaited()

    async def test_service_failure_is_reported_not_raised(self, mock_context):
        update = _make_update()
        mock_context.args = ["sometoken"]
        with patch("apps.bot.handlers.common.start.services") as svc:
            svc.link_telegram_by_token = AsyncMock(side_effect=Exception("redis down"))
            await start(update, mock_context)
        update.message.reply_text.assert_awaited_once()
