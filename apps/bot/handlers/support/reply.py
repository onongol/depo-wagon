import logging
from typing import TYPE_CHECKING

from .text import (
    build_support_reply_delivered_text,
    build_support_reply_failed_text,
    build_support_reply_header,
    build_support_reply_text,
)
from .utils import lookup_request

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.storage.redis import RedisStorage
    from aiogram.types import Message

logger = logging.getLogger(__name__)


async def support_reply(message: Message, bot: Bot, fsm_storage: RedisStorage) -> None:
    """Relay a support member's reply back to the user who asked.

    Text goes under the reply header; any other content is copied after it.
    The outcome is a reply, so the group sees which answer it refers to.
    """
    replied_to = message.reply_to_message
    if replied_to is None:
        return

    user_id = await lookup_request(fsm_storage, message.chat.id, replied_to.message_id)
    if user_id is None:
        return

    try:
        if message.text:
            await bot.send_message(
                chat_id=user_id, **build_support_reply_text(message.text).as_kwargs()
            )
        else:
            await bot.send_message(
                chat_id=user_id, **build_support_reply_header().as_kwargs()
            )
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
    except Exception:
        logger.exception(
            "Failed to deliver support reply to request %s", replied_to.message_id
        )
        await message.reply(**build_support_reply_failed_text().as_kwargs())
        return

    await message.reply(**build_support_reply_delivered_text().as_kwargs())
