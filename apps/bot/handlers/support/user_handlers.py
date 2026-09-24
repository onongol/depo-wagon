"""User-facing side of support: the /support dialog that relays a question."""

import html
import logging
from typing import TYPE_CHECKING

from apps.bot.messages import BotMessages as M
from apps.bot.states import SupportSG

from .utils import remember_request, support_chat_id

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

    from apps.core.models import Employee

logger = logging.getLogger(__name__)


async def support_start(message: Message, state: FSMContext) -> None:
    """Entry: /support — ask the user to type their question."""
    if support_chat_id() is None:
        await message.answer(str(M.SUPPORT_UNAVAILABLE), parse_mode=M.PARSE_MODE)
        return

    await message.answer(str(M.SUPPORT_ASK), parse_mode=M.PARSE_MODE)
    await state.set_state(SupportSG.message)


async def support_receive(
    message: Message, state: FSMContext, bot: Bot, employee: Employee | None
) -> None:
    """Relay the user's question to the support chat with their identity."""
    chat_id = support_chat_id()
    if chat_id is None:
        await message.answer(str(M.SUPPORT_UNAVAILABLE), parse_mode=M.PARSE_MODE)
        await state.set_state(None)
        return

    question = message.text.strip()
    user = message.from_user

    if employee:
        identity = (
            f"{employee.full_name} "
            f"({employee.employee_id}, {employee.get_role_display()})"
        )
    else:
        identity = user.full_name or user.first_name

    text = str(M.SUPPORT_REQUEST).format(
        identity=html.escape(identity),
        username=f"@{user.username}" if user.username else "—",
        question=html.escape(question),
    )

    try:
        sent = await bot.send_message(
            chat_id=chat_id, text=text, parse_mode=M.PARSE_MODE
        )
    except Exception:
        logger.exception(
            "Failed to relay support request from %s",
            f"employee {employee.id}" if employee else "an unlinked chat",
        )
        await message.answer(str(M.SUPPORT_UNAVAILABLE), parse_mode=M.PARSE_MODE)
        await state.set_state(None)
        return

    await remember_request(sent.message_id, user.id)

    await message.answer(str(M.SUPPORT_SENT))
    await state.set_state(None)
