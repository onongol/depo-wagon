"""Support-group side: route a support member's reply back to the user."""

import html
import logging
from typing import TYPE_CHECKING

from apps.bot.messages import BotMessages as M

from .utils import lookup_request

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.types import Message

logger = logging.getLogger(__name__)


async def support_reply(message: Message, bot: Bot) -> None:
    """Relay a support member's reply (in the group) back to the original user.

    Handles any content type: plain text gets a formatted message; media
    (photo, voice, sticker, document, …) is delivered via copy_message.

    Replies with message.reply, not message.answer — this runs in the support
    group, where PTB's reply_text quoted the message being answered.
    """
    replied_to = message.reply_to_message
    if replied_to is None:
        return

    user_id = await lookup_request(replied_to.message_id)
    if user_id is None:
        return

    try:
        if message.text:
            await bot.send_message(
                chat_id=user_id,
                text=str(M.SUPPORT_REPLY).format(text=html.escape(message.text)),
                parse_mode=M.PARSE_MODE,
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=str(M.SUPPORT_REPLY_HEADER),
                parse_mode=M.PARSE_MODE,
            )
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
    except Exception:
        logger.exception("Failed to deliver support reply to %s", user_id)
        await message.reply(str(M.SUPPORT_REPLY_FAILED))
        return

    await message.reply(str(M.SUPPORT_REPLY_DELIVERED))
