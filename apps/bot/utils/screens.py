import logging
from typing import TYPE_CHECKING, Any

from aiogram.exceptions import TelegramBadRequest

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import CallbackQuery, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in exc.message.lower()


def _is_uneditable(exc: TelegramBadRequest) -> bool:
    """The message is gone or too old; any other 400 is about the screen itself."""
    msg = exc.message.lower()
    return "message to edit not found" in msg or "message can't be edited" in msg


def clamp_page(total: int, page: int, page_size: int) -> tuple[int, int]:
    """Number of pages, never less than one, and page pulled into range."""
    total_pages = max(1, (total + page_size - 1) // page_size)
    return total_pages, max(0, min(page, total_pages - 1))


async def send_screen(send: Callable[..., Awaitable], text: str, **kwargs: Any) -> None:
    """Send or edit in place; an edit that would change nothing is not an error."""
    try:
        await send(text, **kwargs)
    except TelegramBadRequest as exc:
        if not _is_not_modified(exc):
            raise


async def edit_or_send(
    callback: CallbackQuery,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    **kwargs: Any,
) -> None:
    """Replace the button's message, or send the screen anew when it can't be.

    Edits by chat and message id, so an InaccessibleMessage is tried too. Only an
    inline keyboard can ride an edit; a reply keyboard needs its own message.
    """
    message = callback.message
    if message is None:
        await callback.bot.send_message(
            callback.from_user.id, reply_markup=reply_markup, **kwargs
        )
        return

    try:
        await callback.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=reply_markup,
            **kwargs,
        )
    except TelegramBadRequest as exc:
        if _is_not_modified(exc):
            return
        if not _is_uneditable(exc):
            raise
        logger.info("Message refused the edit, sending anew: %s", exc.message)
    else:
        return

    await message.answer(reply_markup=reply_markup, **kwargs)
