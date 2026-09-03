"""Support-group side: route a support member's reply back to the user."""

import html
import logging
from typing import TYPE_CHECKING

from apps.bot.messages import BotMessages as M

from .utils import lookup_request

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Relay a support member's reply (in the group) back to the original user.

    Handles any content type: plain text gets a formatted message; media
    (photo, voice, sticker, document, …) is delivered via copy_message.
    """
    message = update.message
    replied_to = message.reply_to_message
    if replied_to is None:
        return

    user_id = await lookup_request(replied_to.message_id)
    if user_id is None:
        return

    try:
        if message.text:
            await context.bot.send_message(
                chat_id=user_id,
                text=str(M.SUPPORT_REPLY).format(text=html.escape(message.text)),
                parse_mode=M.PARSE_MODE,
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=str(M.SUPPORT_REPLY_HEADER),
                parse_mode=M.PARSE_MODE,
            )
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat_id,
                message_id=message.message_id,
            )
    except Exception:
        logger.exception("Failed to deliver support reply to %s", user_id)
        await message.reply_text(str(M.SUPPORT_REPLY_FAILED))
        return

    await message.reply_text(str(M.SUPPORT_REPLY_DELIVERED))
