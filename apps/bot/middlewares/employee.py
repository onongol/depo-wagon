import logging
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from apps.bot import services
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


async def _announce_failure(event: TelegramObject) -> None:
    text = str(M.SESSION_ERROR)

    if isinstance(event, Message):
        await event.answer(text)
        return

    if isinstance(event, CallbackQuery):
        await event.answer()
        if event.message is not None:
            await event.message.answer(text)


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

        try:
            data["employee"] = (
                await services.get_employee_by_telegram_id(user.id) if user else None
            )
        except Exception:
            logger.exception("Employee lookup failed for user %s", user.id)
            await _announce_failure(event)
            return None

        return await handler(event, data)
