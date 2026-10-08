import asyncio
import contextlib
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError
from aiogram.utils.formatting import Text
from google.genai.errors import ServerError

from apps.ai_service.rag.chat import ContentBlockedError, answer_question
from apps.bot.constants import UD_AI_CHAT_HISTORY
from apps.bot.utils.unregistered import refuse_unregistered

from .text import (
    build_ai_chat_blocked_text,
    build_ai_chat_error_text,
    build_ai_chat_overloaded_text,
    build_ai_chat_thinking_text,
)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

    from apps.core.models import Employee

logger = logging.getLogger(__name__)

_HISTORY_KEEP = 4
_ANSWER_TIMEOUT = 60.0
_MAX_MESSAGE_LEN = 4096


async def _safe_edit(msg: Message, text: Text) -> None:
    with contextlib.suppress(TelegramAPIError):
        await msg.edit_text(**text.as_kwargs())


async def ai_chat_receive(
    message: Message, state: FSMContext, employee: Employee | None
) -> None:
    """Answer a user question through the RAG generator and reply with it.

    An AI failure never leaves the conversation: it edits the placeholder and
    stays in AiChatSG.chatting, so the user can just ask again. A chat that
    lost its employee mid-session does leave it.
    """
    if not employee:
        await state.clear()
        with contextlib.suppress(TelegramAPIError):
            await refuse_unregistered(message)
        return

    question = message.text.strip()

    try:
        thinking_msg = await message.answer(**build_ai_chat_thinking_text().as_kwargs())
    except TelegramAPIError:
        logger.warning("Could not send the AI chat thinking message")
        return

    history: list[dict] = (await state.get_data()).get(UD_AI_CHAT_HISTORY, [])

    try:
        answer = await asyncio.wait_for(
            answer_question(question, history), timeout=_ANSWER_TIMEOUT
        )
    except TimeoutError:
        logger.warning("AI chat timed out after %.0fs", _ANSWER_TIMEOUT)
        await _safe_edit(thinking_msg, build_ai_chat_overloaded_text())
        return
    except ContentBlockedError:
        await _safe_edit(thinking_msg, build_ai_chat_blocked_text())
        return
    except ServerError as e:
        if e.code == HTTPStatus.SERVICE_UNAVAILABLE:
            logger.warning("AI chat 503 overloaded")
            await _safe_edit(thinking_msg, build_ai_chat_overloaded_text())
        else:
            logger.exception("AI chat server error")
            await _safe_edit(thinking_msg, build_ai_chat_error_text())
        return
    except Exception:
        logger.exception("AI chat failed")
        await _safe_edit(thinking_msg, build_ai_chat_error_text())
        return

    if len(answer) > _MAX_MESSAGE_LEN:
        answer = answer[: _MAX_MESSAGE_LEN - 1] + "…"

    history = history[-_HISTORY_KEEP:]
    history.append({"role": "user", "content": question})
    history.append({"role": "model", "content": answer})
    await state.update_data({UD_AI_CHAT_HISTORY: history})

    await _safe_edit(thinking_msg, Text(answer))
