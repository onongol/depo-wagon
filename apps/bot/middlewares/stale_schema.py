import logging
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from apps.bot.constants import UD_DEFECT
from apps.bot.fsm import clear_defect_keys
from apps.bot.handlers.common.utils import edit_or_send
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
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

    with suppress(TelegramBadRequest):
        await event.answer()

    await edit_or_send(event, text=text)


class StaleSchemaMiddleware(BaseMiddleware):
    """Drop a defect form an older build wrote, before any flow step loads it.

    Outer runs ahead of StateFilter, so every feature's updates pass through.
    Outside DefectSG the form is dropped silently and the update goes on;
    inside it the update is swallowed, since a step would dereference None
    and stale_callback would blame the button instead of the form.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext = data["state"]
        stored = (await state.get_data()).get(UD_DEFECT)

        if not stored or is_current_schema(stored):
            return await handler(event, data)

        logger.info("Discarding a defect form written by an older state schema")
        await clear_defect_keys(state)

        if data.get("raw_state") not in DefectSG.__all_states_names__:
            return await handler(event, data)

        await state.set_state(None)
        await _announce(event)
        return None
