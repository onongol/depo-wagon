"""Messages to employees leave the bot as text and entities; the worker sends them."""

from unittest.mock import AsyncMock, call, patch

import pytest
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import MessageEntity
from aiogram.utils.formatting import Bold, Text
from model_bakery import baker

from apps.bot.services import queue_messages
from apps.bot.tasks import _send, send_to_employee_task

CHAT_ID = 987654321
ENTITIES = [{"type": "bold", "offset": 3, "length": 5}]


def _sends(side_effect=None):
    return patch("apps.bot.tasks._send", AsyncMock(side_effect=side_effect))


def _retrying():
    return patch.object(
        send_to_employee_task, "retry", return_value=RuntimeError("retrying")
    )


@pytest.fixture
def employee(db):
    return baker.make("core.Employee", telegram_id=CHAT_ID, is_active=True)


class TestQueueMessages:
    async def test_queues_json_safe_text_and_entities_for_each_employee(self):
        with patch("apps.bot.tasks.send_to_employee_task.delay") as delay:
            await queue_messages([7, 9], Text("🔴 ", Bold("Alert")))

        assert delay.call_args_list == [
            call(7, "🔴 Alert", ENTITIES),
            call(9, "🔴 Alert", ENTITIES),
        ]


class TestSend:
    async def test_the_entities_reach_telegram_as_message_entities(self):
        bot = AsyncMock()
        bot.__aenter__.return_value = bot

        with patch("apps.bot.bot.make_bot", return_value=bot):
            await _send(CHAT_ID, "🔴 Alert", ENTITIES)

        bot.send_message.assert_awaited_once_with(
            chat_id=CHAT_ID,
            text="🔴 Alert",
            entities=[MessageEntity(type="bold", offset=3, length=5)],
        )


class TestSendToEmployeeTask:
    def test_sends_to_the_employees_chat(self, employee):
        with _sends() as send:
            send_to_employee_task(employee.id, "text", ENTITIES)

        send.assert_awaited_once_with(CHAT_ID, "text", ENTITIES)

    @pytest.mark.parametrize(
        "fields",
        [{"telegram_id": None}, {"is_active": False}],
        ids=["unlinked", "inactive"],
    )
    def test_an_unlinked_or_inactive_employee_gets_nothing(self, db, fields):
        employee = baker.make("core.Employee", **{"telegram_id": CHAT_ID, **fields})

        with _sends() as send:
            send_to_employee_task(employee.id, "text", ENTITIES)

        send.assert_not_called()

    def test_a_rate_limit_retries_when_telegram_says(self, employee):
        limited = TelegramRetryAfter(method=None, message="Too Many", retry_after=7)

        with (
            _sends(limited),
            _retrying() as retry,
            pytest.raises(RuntimeError, match="retrying"),
        ):
            send_to_employee_task(employee.id, "text", ENTITIES)

        retry.assert_called_once_with(exc=limited, countdown=7)

    @pytest.mark.parametrize(
        "error",
        [
            TelegramNetworkError(method=None, message="timeout"),
            TelegramServerError(method=None, message="Bad Gateway"),
        ],
        ids=["network", "server"],
    )
    def test_an_outage_retries_with_backoff(self, employee, error):
        with (
            _sends(error),
            _retrying() as retry,
            pytest.raises(RuntimeError, match="retrying"),
        ):
            send_to_employee_task(employee.id, "text", ENTITIES)

        retry.assert_called_once_with(exc=error, countdown=60)

    def test_a_refusal_is_logged_by_employee_id_not_retried(self, db, caplog):
        employee = baker.make(
            "core.Employee", telegram_id=CHAT_ID, first_name="Oyuntsetseg"
        )
        blocked = TelegramForbiddenError(method=None, message="blocked")

        with _sends(blocked), patch.object(send_to_employee_task, "retry") as retry:
            send_to_employee_task(employee.id, "text", ENTITIES)

        retry.assert_not_called()
        assert f"employee {employee.id}" in caplog.text
        assert "Oyuntsetseg" not in caplog.text
        assert str(CHAT_ID) not in caplog.text
