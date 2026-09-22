from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware

from apps.bot import services

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject


class EmployeeMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if "employee" not in data["handler"].params:
            return await handler(event, data)

        user = data.get("event_from_user")
        data["employee"] = (
            await services.get_employee_by_telegram_id(user.id) if user else None
        )

        return await handler(event, data)
