import logging
from typing import TYPE_CHECKING

from telegram.error import TelegramError

from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def stale_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answer a button whose callback data the bot no longer holds.

    arbitrary_callback_data keeps the payload in this process, so every button
    sent before a restart comes back as InvalidCallbackData. Without this the
    tap would spin and then go quiet, leaving nothing to act on.
    """
    query = update.callback_query
    await query.answer()

    try:
        await query.edit_message_text(str(M.BUTTON_EXPIRED))
    except TelegramError:
        logger.debug("Could not replace a stale keyboard (message deleted or too old)")
