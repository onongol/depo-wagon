"""Reset a defect form that an earlier build's models wrote.

Stored state is discarded rather than migrated, so DefectData.from_dict returns
None for a foreign schema. Only six of the flow's twenty-odd steps check that
None; the rest assign straight onto the form. So the reset has to happen ahead
of the handler, not inside it — an outer middleware on the flow router, the
same shape AiChatTimeoutMiddleware uses.

Swallowing the update rather than returning UNHANDLED: the fall-through for a
callback is unroutable_button, which is deliberately silent, and silence is the
wrong answer to a form that just vanished.
"""

import logging
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

    await event.answer()

    if event.message is None:
        return

    try:
        await event.message.edit_text(text)
    except TelegramAPIError:
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
