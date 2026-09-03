import logging

from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


# PTB awaits error handlers, so this stays async with nothing to await.
async def error_handler(  # noqa: RUF029
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    logger.error("Unhandled exception in update %s", update, exc_info=context.error)
