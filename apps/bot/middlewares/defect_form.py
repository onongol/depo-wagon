import logging
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from apps.bot.constants import UD_DEFECT
from apps.bot.fsm import clear_defect_keys
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.user_data import is_current_schema
from apps.bot.utils.screens import edit_or_send

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext
    from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


async def _announce(event: TelegramObject, text: str) -> None:
    if isinstance(event, Message):
        await event.answer(text)
        return

    if not isinstance(event, CallbackQuery):
        return

    with suppress(TelegramBadRequest):
        await event.answer()

    await edit_or_send(event, text=text)


class DefectFormMiddleware(BaseMiddleware):
    """Inside DefectSG a step always has a form to load, so none checks for None.

    Outer runs ahead of StateFilter, so every feature's updates pass through.
    A form an older build wrote is dropped wherever it is found, silently
    outside DefectSG. Inside it, a dropped or missing form ends the flow here,
    and stale_callback never gets to blame the button instead of the form.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext = data["state"]
        stored = (await state.get_data()).get(UD_DEFECT)

        if stored and is_current_schema(stored):
            return await handler(event, data)

        if stored:
            logger.info("Discarding a defect form written by an older state schema")
            await clear_defect_keys(state)

        if data.get("raw_state") not in DefectSG.__all_states_names__:
            return await handler(event, data)

        if not stored:
            logger.warning("A defect step was reached without its form")
        await state.set_state(None)
        await _announce(event, str(M.FORM_OUTDATED if stored else M.DEFECT_CANCELLED))
        return None
