import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramForbiddenError

from .text import (
    build_support_reply_blocked_text,
    build_support_reply_delivered_text,
    build_support_reply_header,
    build_support_reply_retry_text,
    build_support_request_unknown_text,
)
from .utils import lookup_request

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.storage.redis import RedisStorage
    from aiogram.types import Message

logger = logging.getLogger(__name__)


async def support_reply(message: Message, bot: Bot, fsm_storage: RedisStorage) -> None:
    """Copy a support member's reply, under a header, to the user who asked."""
    replied_to = message.reply_to_message
    if replied_to is None:
        return

    user_id = await lookup_request(fsm_storage, message.chat.id, replied_to.message_id)
    if user_id is None:
        # Operators talking among themselves reply to each other, not to the bot
        if replied_to.from_user is not None and replied_to.from_user.id == bot.id:
            await message.reply(**build_support_request_unknown_text().as_kwargs())
        return

    try:
        await bot.send_message(
            chat_id=user_id, **build_support_reply_header().as_kwargs()
        )
        await bot.copy_message(
            chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id
        )
    except TelegramForbiddenError:
        logger.warning("Support reply refused: the user blocked the bot")
        await message.reply(**build_support_reply_blocked_text().as_kwargs())
        return
    except Exception:
        logger.exception("Failed to deliver a support reply")
        await message.reply(**build_support_reply_retry_text().as_kwargs())
        return

    await message.reply(**build_support_reply_delivered_text().as_kwargs())
