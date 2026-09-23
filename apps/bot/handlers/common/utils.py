import logging
from typing import TYPE_CHECKING, Any

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InaccessibleMessage

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)


def clamp_page(total: int, page: int, page_size: int) -> tuple[int, int]:
    """Number of pages, never less than one, and page pulled into range."""
    total_pages = max(1, (total + page_size - 1) // page_size)
    return total_pages, max(0, min(page, total_pages - 1))


async def send_screen(send: Callable[..., Awaitable], text: str, **kwargs: Any) -> None:
    """Send or edit in place; an edit that would change nothing is not an error."""
    try:
        await send(text, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" not in exc.message.lower():
            raise


async def edit_or_send(callback: CallbackQuery, **kwargs: Any) -> None:
    """Replace the button's message, or send the screen anew when it can't be.

    The flow has already moved on, so the screen must reach the user even when
    the message is gone, inaccessible (no edit methods) or too old to edit.
    """
    message = callback.message
    if message is None:
        await callback.bot.send_message(callback.from_user.id, **kwargs)
        return

    if not isinstance(message, InaccessibleMessage):
        try:
            await message.edit_text(**kwargs)
        except TelegramBadRequest as exc:
            if "message is not modified" in exc.message.lower():
                return
            logger.info("Message refused the edit, sending anew: %s", exc.message)
        else:
            return

    await message.answer(**kwargs)
