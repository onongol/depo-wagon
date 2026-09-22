from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from django.db import close_old_connections

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject


class CloseOldConnectionsMiddleware(BaseMiddleware):
    """Register only on dp.update — fires once per Update, ahead of every filter."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        close_old_connections()
        return await handler(event, data)
