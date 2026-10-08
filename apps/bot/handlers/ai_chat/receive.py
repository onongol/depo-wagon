import asyncio
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from aiogram import flags
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.utils.formatting import Text
from google.genai.errors import APIError

from apps.ai_service.rag.chat import ContentBlockedError, answer_question
from apps.bot.constants import UD_AI_CHAT_HISTORY
from apps.bot.utils.formatting import split_message

from .text import (
    build_ai_chat_blocked_text,
    build_ai_chat_error_text,
    build_ai_chat_overloaded_text,
    build_ai_chat_text_only_text,
    build_ai_chat_thinking_text,
)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

logger = logging.getLogger(__name__)

_HISTORY_KEEP = 4
_ANSWER_TIMEOUT = 60.0

_OVERLOADED = frozenset({HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.SERVICE_UNAVAILABLE})


def _from_model(answer: str) -> tuple[list[Text], str | None]:
    """The answer in messages that each fit; an empty one, which Telegram
    refuses, as the error."""
    if not answer.strip():
        logger.warning("AI chat got an empty answer")
        return [build_ai_chat_error_text()], None

    return [Text(piece) for piece in split_message(answer)], answer


async def _ask(question: str, history: list[dict]) -> tuple[list[Text], str | None]:
    """The replies to show, and the model's answer when there is one to remember."""
    try:
        answer = await asyncio.wait_for(
            answer_question(question, history), timeout=_ANSWER_TIMEOUT
        )
    except TimeoutError:
        logger.warning("AI chat timed out after %.0fs", _ANSWER_TIMEOUT)
        return [build_ai_chat_overloaded_text()], None
    except ContentBlockedError:
        return [build_ai_chat_blocked_text()], None
    except APIError as e:
        if e.code in _OVERLOADED:
            logger.warning("AI chat overloaded: %s", e.code)
            return [build_ai_chat_overloaded_text()], None
        logger.exception("AI chat API error")
        return [build_ai_chat_error_text()], None
    except Exception:
        logger.exception("AI chat failed")
        return [build_ai_chat_error_text()], None

    return _from_model(answer)


async def _show(placeholder: Message, replies: list[Text]) -> bool:
    """The first reply in place of the placeholder, or under it if the edit is
    refused; the rest follow it as new messages."""
    first, *rest = replies
    try:
        await placeholder.edit_text(**first.as_kwargs())
    except TelegramBadRequest as exc:
        logger.info("AI chat placeholder refused the edit: %s", exc.message)
        rest = replies
    except TelegramAPIError as exc:
        logger.warning("Could not show the AI chat reply: %s", exc)
        return False

    try:
        for reply in rest:
            await placeholder.answer(**reply.as_kwargs())
    except TelegramAPIError as exc:
        logger.warning("Could not show the AI chat reply: %s", exc)
        return False
    return True


@flags.registered
async def ai_chat_receive(message: Message, state: FSMContext) -> None:
    """Answer the question; a failure keeps the session open for another try."""
    question = message.text.strip()
    if not question:
        await message.answer(**build_ai_chat_text_only_text().as_kwargs())
        return

    try:
        thinking_msg = await message.answer(**build_ai_chat_thinking_text().as_kwargs())
    except TelegramAPIError:
        logger.warning("Could not send the AI chat thinking message")
        return

    history: list[dict] = (await state.get_data()).get(UD_AI_CHAT_HISTORY, [])

    replies, answer = await _ask(question, history)
    if not await _show(thinking_msg, replies) or answer is None:
        return

    history = history[-_HISTORY_KEEP:]
    history.append({"role": "user", "content": question})
    history.append({"role": "model", "content": answer})
    await state.update_data({UD_AI_CHAT_HISTORY: history})


async def ai_chat_not_text(message: Message) -> None:
    """A photo, voice note or sticker in place of the question: ask for text."""
    await message.answer(**build_ai_chat_text_only_text().as_kwargs())
