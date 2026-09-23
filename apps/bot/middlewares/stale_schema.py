import logging
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message

from apps.bot.constants import UD_DEFECT
from apps.bot.fsm import clear_defect_keys
from apps.bot.messages import BotMessages as M
from apps.bot.user_data import is_current_schema

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext
    from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


async def _announce(event: TelegramObject) -> None:
    text = str(M.FORM_OUTDATED)

    if isinstance(event, Message):
        await event.answer(text)
        return

    if not isinstance(event, CallbackQuery):
        return

    with suppress(TelegramAPIError):
        await event.answer()

    if event.message is None:
        return

    if isinstance(event.message, Message):
        with suppress(TelegramAPIError):
            await event.message.edit_text(text)
            return

    await event.message.answer(text)


class StaleSchemaMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext = data["state"]
        stored = (await state.get_data()).get(UD_DEFECT)

        if stored and not is_current_schema(stored):
            logger.info("Discarding a defect form written by an older state schema")
            await clear_defect_keys(state)
            await state.set_state(None)
            await _announce(event)
            return None

        return await handler(event, data)
