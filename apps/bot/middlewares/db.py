from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from django.db import close_old_connections

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject


class CloseOldConnectionsMiddleware(BaseMiddleware):
    """Drop connections that outlived CONN_MAX_AGE before handling an update.

    Register on dp.update — the only observer that fires exactly once per
    Update and ahead of every filter. That is where PTB did it, by overriding
    Application.process_update.

    Only before, as PTB did. Closing afterwards as well would be defensible but
    is a behaviour change, and the long-lived poller has one connection to keep
    warm rather than a request pool to return to.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        close_old_connections()
        return await handler(event, data)
