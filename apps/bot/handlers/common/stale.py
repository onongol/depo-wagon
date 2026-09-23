import logging
from contextlib import suppress
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramBadRequest

from apps.bot.handlers.common.text import (
    build_button_expired_text,
    build_unhandled_message_text,
)

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)


async def noop_button(callback: CallbackQuery) -> None:
    with suppress(TelegramBadRequest):
        await callback.answer()


async def stale_button(callback: CallbackQuery, bot: Bot) -> None:
    """Tell the user the button is dead and take it off the screen.

    Edits by chat and message id rather than through callback.message, which by
    definition may be an InaccessibleMessage here — this handler exists for old
    messages. A 400 here is a refusal about this one message or query and is
    expected; anything else reaches error_handler.
    """
    with suppress(TelegramBadRequest):
        await callback.answer()

    if callback.message is None:
        return

    with suppress(TelegramBadRequest):
        await bot.edit_message_text(
            **build_button_expired_text().as_kwargs(),
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
        )


async def unhandled_message(message: Message, state: FSMContext) -> None:
    """Answer a private message no router claimed, instead of going quiet.

    Reached only outside every known state (the router filters with
    ~StateFilter(*ALL_GROUPS)): an expired FSM key, or a state string left by
    an older build.
    """
    current = await state.get_state()

    if current is not None:
        logger.warning("Clearing an FSM state this build does not know: %s", current)
        await state.clear()

    await message.answer(**build_unhandled_message_text().as_kwargs())
