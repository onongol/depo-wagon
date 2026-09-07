import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


# PTB awaits error handlers, so this stays async with nothing to await.
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception in update %s", update, exc_info=context.error)
