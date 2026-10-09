import asyncio
import logging
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

SHUTDOWN_DRAIN_TIMEOUT = 90.0


class InFlightMiddleware(BaseMiddleware):
    """Track each update's task so shutdown can wait for the ones still running.

    Register on dp.update: with handle_as_tasks every update runs in a task of
    its own, so awaiting that task covers the whole chain, wherever this sits.
    """

    def __init__(self, drain_timeout: float = SHUTDOWN_DRAIN_TIMEOUT) -> None:
        self.drain_timeout = drain_timeout
        self.tasks: set[asyncio.Task[Any]] = set()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        task = asyncio.current_task()

        if task is None:
            return await handler(event, data)

        self.tasks.add(task)
        try:
            return await handler(event, data)
        finally:
            self.tasks.discard(task)

    async def drain(self) -> None:
        """Takes no parameters: aiogram would fill them from the shutdown kwargs."""
        if not self.tasks:
            return

        logger.info("Waiting for %d update(s) to finish", len(self.tasks))
        _, pending = await asyncio.wait(set(self.tasks), timeout=self.drain_timeout)

        if pending:
            logger.warning(
                "%d update(s) still running after %ss, cancelling",
                len(pending),
                self.drain_timeout,
            )
