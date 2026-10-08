from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.fsm.scene import SceneHandlerWrapper

from apps.bot import services
from apps.bot.utils.unregistered import refuse_unregistered

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.dispatcher.event.handler import HandlerObject
    from aiogram.fsm.context import FSMContext
    from aiogram.types import TelegramObject


def _takes_employee(handler: HandlerObject) -> bool:
    """A scene's handler is wrapped, and the wrapper takes **kwargs."""
    if isinstance(handler.callback, SceneHandlerWrapper):
        return "employee" in handler.callback.handler.params
    return "employee" in handler.params


class EmployeeMiddleware(BaseMiddleware):
    """A handler flagged @flags.registered is refused here rather than handed None.

    The refusal ends the chat's flow, as /cancel does: a chat whose employee was
    unlinked mid-session would otherwise be refused at every message.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        registered = get_flag(data, "registered", default=False)
        if not (registered or _takes_employee(data["handler"])):
            return await handler(event, data)

        user = data.get("event_from_user")
        employee = await services.get_employee_by_telegram_id(user.id) if user else None

        if registered and employee is None:
            state: FSMContext | None = data.get("state")
            if state is not None:
                await state.clear()
            await refuse_unregistered(event)
            return None

        data["employee"] = employee
        return await handler(event, data)
