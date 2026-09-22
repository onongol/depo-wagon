import logging
from contextlib import suppress
from typing import TYPE_CHECKING

from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError

from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram.types import ErrorEvent, Update

logger = logging.getLogger(__name__)


async def _tell_the_user(update: Update) -> None:
    """Private chats only; an expired query must not cost the message."""
    message = update.message

    if update.callback_query is not None:
        with suppress(TelegramAPIError):
            await update.callback_query.answer()
        message = update.callback_query.message

    if message is None or message.chat.type != ChatType.PRIVATE:
        return

    with suppress(TelegramAPIError):
        await message.answer(str(M.SESSION_ERROR))


async def error_handler(event: ErrorEvent) -> None:
    """Log, tell the user, swallow."""
    logger.error(
        "Unhandled exception in update %s", event.update, exc_info=event.exception
    )
    await _tell_the_user(event.update)
