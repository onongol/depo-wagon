from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.fsm.scene import SceneHandlerWrapper

from apps.bot import services

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.dispatcher.event.handler import HandlerObject
    from aiogram.types import TelegramObject


def _takes_employee(handler: HandlerObject) -> bool:
    """A scene's handler is wrapped, and the wrapper takes **kwargs."""
    if isinstance(handler.callback, SceneHandlerWrapper):
        return "employee" in handler.callback.handler.params
    return "employee" in handler.params


class EmployeeMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not _takes_employee(data["handler"]):
            return await handler(event, data)

        user = data.get("event_from_user")
        data["employee"] = (
            await services.get_employee_by_telegram_id(user.id) if user else None
        )

        return await handler(event, data)
