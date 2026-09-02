from unittest.mock import AsyncMock, patch

from telegram.ext import Application, CallbackQueryHandler

from apps.bot.application import _BotApplication, create_application
from apps.bot.callbacks import LinkCancelCB, LinkConfirmCB


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


class TestLinkButtonsAreRegistered:
    """Handler tests call the callbacks directly; only this proves they are wired."""

    def test_link_callbacks_reach_a_handler(self, settings):
        settings.TELEGRAM_BOT_TOKEN = "123456:ABCdefGHI"
        app = create_application()

        patterns = [
            h.pattern
            for h in app.handlers[0]
            if isinstance(h, CallbackQueryHandler) and callable(h.pattern)
        ]

        assert any(p(LinkConfirmCB(employee_id=1)) for p in patterns)
        assert any(p(LinkCancelCB()) for p in patterns)
