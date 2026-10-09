from unittest.mock import AsyncMock, MagicMock, call

import pytest
from aiogram.exceptions import (
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
    TelegramUnauthorizedError,
)
from aiogram.methods import DeleteWebhook

from apps.bot.management.commands import run_bot
from apps.bot.management.commands.run_bot import WEBHOOK_ATTEMPTS, _delete_webhook


def _network_error():
    return TelegramNetworkError(method=DeleteWebhook(), message="network")


@pytest.fixture
def bot():
    bot = MagicMock()
    bot.delete_webhook = AsyncMock()
    return bot


@pytest.fixture
def sleep(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(run_bot.asyncio, "sleep", sleep)
    return sleep


class TestDeleteWebhook:
    async def test_passes_drop_pending_through(self, bot, sleep):
        await _delete_webhook(bot, drop_pending=True)

        bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=True)
        sleep.assert_not_awaited()

    async def test_retries_a_network_error_with_backoff(self, bot, sleep):
        bot.delete_webhook.side_effect = [_network_error(), _network_error(), None]

        await _delete_webhook(bot, drop_pending=False)

        assert bot.delete_webhook.await_count == 3
        assert sleep.await_args_list == [call(1.0), call(2.0)]

    async def test_retries_a_server_error(self, bot, sleep):
        bot.delete_webhook.side_effect = [
            TelegramServerError(method=DeleteWebhook(), message="Bad Gateway"),
            None,
        ]

        await _delete_webhook(bot, drop_pending=False)

        assert bot.delete_webhook.await_count == 2

    async def test_waits_as_long_as_flood_control_asks(self, bot, sleep):
        bot.delete_webhook.side_effect = [
            TelegramRetryAfter(method=DeleteWebhook(), message="flood", retry_after=3),
            None,
        ]

        await _delete_webhook(bot, drop_pending=False)

        sleep.assert_awaited_once_with(3)

    async def test_gives_up_after_the_last_attempt(self, bot, sleep):
        bot.delete_webhook.side_effect = [
            _network_error() for _ in range(WEBHOOK_ATTEMPTS)
        ]

        with pytest.raises(TelegramNetworkError):
            await _delete_webhook(bot, drop_pending=False)

        assert bot.delete_webhook.await_count == WEBHOOK_ATTEMPTS
        assert sleep.await_count == WEBHOOK_ATTEMPTS - 1

    async def test_does_not_retry_a_rejected_token(self, bot, sleep):
        bot.delete_webhook.side_effect = TelegramUnauthorizedError(
            method=DeleteWebhook(), message="Unauthorized"
        )

        with pytest.raises(TelegramUnauthorizedError):
            await _delete_webhook(bot, drop_pending=False)

        bot.delete_webhook.assert_awaited_once()
        sleep.assert_not_awaited()
