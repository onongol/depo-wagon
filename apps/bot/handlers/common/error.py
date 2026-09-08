import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)


async def error_handler(event: ErrorEvent) -> None:
    """Log and swallow. Returning anything but UNHANDLED stops the propagation."""
    logger.error(
        "Unhandled exception in update %s", event.update, exc_info=event.exception
    )
