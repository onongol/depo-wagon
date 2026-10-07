import logging
from typing import TYPE_CHECKING

from .text import (
    build_support_request_text,
    build_support_sent_text,
    build_support_unavailable_text,
)
from .utils import remember_request, support_chat_id

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

    from apps.core.models import Employee

logger = logging.getLogger(__name__)


async def support_receive(
    message: Message, state: FSMContext, bot: Bot, employee: Employee | None
) -> None:
    """Relay the user's question to the support chat with their identity."""
    chat_id = support_chat_id()
    if chat_id is None:
        await message.answer(**build_support_unavailable_text().as_kwargs())
        await state.set_state(None)
        return

    user = message.from_user
    text = build_support_request_text(message.text.strip(), user, employee)

    try:
        sent = await bot.send_message(chat_id=chat_id, **text.as_kwargs())
    except Exception:
        logger.exception(
            "Failed to relay support request from %s",
            f"employee {employee.id}" if employee else "an unlinked chat",
        )
        await message.answer(**build_support_unavailable_text().as_kwargs())
        await state.set_state(None)
        return

    await remember_request(sent.message_id, user.id)

    await message.answer(**build_support_sent_text().as_kwargs())
    await state.set_state(None)
