"""Tests for the aiogram middlewares."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.bot.middlewares import CloseOldConnectionsMiddleware

TARGET = "apps.bot.middlewares.db.close_old_connections"


class TestCloseOldConnectionsMiddleware:
    async def test_closes_connections_before_the_handler_runs(self):
        order = []
        middleware = CloseOldConnectionsMiddleware()

        async def handler(event, data):
            order.append("handler")
            return "result"

        with patch(TARGET, side_effect=lambda: order.append("close")):
            result = await middleware(handler, MagicMock(), {})

        assert order == ["close", "handler"]
        assert result == "result"

    async def test_passes_the_event_and_data_through_untouched(self):
        middleware = CloseOldConnectionsMiddleware()
        handler = AsyncMock(return_value=None)
        event = MagicMock()
        data = {"state": MagicMock()}

        with patch(TARGET):
            await middleware(handler, event, data)

        handler.assert_awaited_once_with(event, data)

    async def test_does_not_swallow_a_handler_exception(self):
        middleware = CloseOldConnectionsMiddleware()

        async def handler(event, data):
            msg = "boom"
            raise RuntimeError(msg)

        with patch(TARGET), pytest.raises(RuntimeError, match="boom"):
            await middleware(handler, MagicMock(), {})

    async def test_closes_once_per_call_not_per_handler_attempt(self):
        middleware = CloseOldConnectionsMiddleware()

        with patch(TARGET) as close:
            await middleware(AsyncMock(), MagicMock(), {})

        close.assert_called_once()
