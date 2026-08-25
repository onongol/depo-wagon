from unittest.mock import AsyncMock, patch

from telegram.ext import Application

from apps.bot.application import _BotApplication


class TestBotApplication:
    async def test_calls_close_old_connections_before_super(self):
        update = object()
        call_order = []

        with (
            patch(
                "apps.bot.application.close_old_connections",
                side_effect=lambda: call_order.append("close"),
            ),
            patch.object(
                Application,
                "process_update",
                new_callable=AsyncMock,
                side_effect=lambda u: call_order.append("super"),
            ),
        ):
            instance = object.__new__(_BotApplication)
            await _BotApplication.process_update(instance, update)

        assert call_order == ["close", "super"]

    async def test_passes_update_to_super(self):
        update = object()
        with (
            patch("apps.bot.application.close_old_connections"),
            patch.object(
                Application, "process_update", new_callable=AsyncMock
            ) as mock_super,
        ):
            instance = object.__new__(_BotApplication)
            await _BotApplication.process_update(instance, update)

        mock_super.assert_called_once_with(update)
