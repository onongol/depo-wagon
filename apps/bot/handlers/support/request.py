import logging
from contextlib import suppress
from typing import TYPE_CHECKING

from django.conf import settings

from .text import (
    build_support_request_text,
    build_support_sent_text,
    build_support_text_only_text,
    build_support_too_long_text,
    build_support_unavailable_text,
)
from .utils import remember_request

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.redis import RedisStorage
    from aiogram.types import Message
    from aiogram.utils.formatting import Text

    from apps.core.models import Employee

logger = logging.getLogger(__name__)

# Telegram's cap on a message's text, in the UTF-16 units len(Text) counts
_MESSAGE_LIMIT = 4096


async def _relay(bot: Bot, storage: RedisStorage, request: Text, user_id: int) -> bool:
    """Post the request to the support chat and remember who asked."""
    chat_id = settings.TELEGRAM_SUPPORT_CHAT_ID
    if chat_id is None:
        return False

    try:
        sent = await bot.send_message(chat_id=chat_id, **request.as_kwargs())
    except Exception:
        logger.exception("Failed to relay a support request")
        return False

    try:
        await remember_request(storage, chat_id, sent.message_id, user_id)
    except Exception:
        # A request nobody can answer by reply would sit in the group for nothing
        logger.exception("Failed to store a support request")
        with suppress(Exception):
            await bot.delete_message(chat_id=chat_id, message_id=sent.message_id)
        return False

    return True


async def support_receive(
    message: Message,
    state: FSMContext,
    bot: Bot,
    employee: Employee | None,
    fsm_storage: RedisStorage,
) -> None:
    """Relay the user's question to the support chat with their identity."""
    question = message.text.strip()
    if not question:
        await message.answer(**build_support_text_only_text().as_kwargs())
        return

    user = message.from_user
    request = build_support_request_text(question, user, employee)
    if len(request) > _MESSAGE_LIMIT:
        await message.answer(**build_support_too_long_text().as_kwargs())
        return

    relayed = await _relay(bot, fsm_storage, request, user.id)

    answer = build_support_sent_text() if relayed else build_support_unavailable_text()
    await message.answer(**answer.as_kwargs())
    await state.set_state(None)


async def support_not_text(message: Message) -> None:
    """A photo, voice note or sticker in place of the question: ask for text."""
    await message.answer(**build_support_text_only_text().as_kwargs())
