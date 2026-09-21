from typing import TYPE_CHECKING, Any

from aiogram.exceptions import TelegramBadRequest

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


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
