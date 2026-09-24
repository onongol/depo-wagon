import logging
from contextlib import suppress
from typing import TYPE_CHECKING

from aiogram.enums import ChatType

from apps.bot.handlers.common.text import build_session_error_text

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.types import Chat, ErrorEvent

logger = logging.getLogger(__name__)


async def error_handler(
    event: ErrorEvent, bot: Bot, event_chat: Chat | None = None
) -> None:
    """Log, tell the user in a private chat, swallow.

    Nothing here may raise: aiogram's ClientDecodeError is not a TelegramAPIError.
    """
    logger.error(
        "Unhandled exception in update_id=%s",
        event.update.update_id,
        exc_info=event.exception,
    )

    if event.update.callback_query is not None:
        with suppress(Exception):
            await event.update.callback_query.answer()

    if event_chat is None or event_chat.type != ChatType.PRIVATE:
        return

    with suppress(Exception):
        await bot.send_message(event_chat.id, **build_session_error_text().as_kwargs())
