import asyncio
import contextlib
import logging
import time
from http import HTTPStatus
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError
from google.genai.errors import ServerError

from apps.ai_service.rag.chat import ContentBlockedError, answer_question
from apps.bot.constants import UD_AI_CHAT_HISTORY, UD_AI_CHAT_LAST
from apps.bot.fsm import user_lock
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

logger = logging.getLogger(__name__)

_HISTORY_KEEP = 4
_ANSWER_TIMEOUT = 60.0
_MAX_MESSAGE_LEN = 4096


async def _safe_edit(msg: Message, text: str) -> None:
    with contextlib.suppress(TelegramAPIError):
        await msg.edit_text(text)


async def ai_chat_receive(message: Message, state: FSMContext) -> None:
    """Answer a user question through the RAG generator and reply with it.

    Never leaves the conversation: every failure path edits the placeholder and
    stays in AiChatSG.chatting, so the user can just ask again.
    """
    question = message.text.strip()
    user_id = message.from_user.id

    try:
        thinking_msg = await message.answer(str(M.AI_CHAT_THINKING))
    except TelegramAPIError:
        logger.warning("Could not send thinking message for user %s", user_id)
        return

    async with user_lock(user_id):
        await state.update_data({UD_AI_CHAT_LAST: time.time()})
        history: list[dict] = (await state.get_data()).get(UD_AI_CHAT_HISTORY, [])

        try:
            answer = await asyncio.wait_for(
                answer_question(question, history), timeout=_ANSWER_TIMEOUT
            )
        except TimeoutError:
            logger.warning(
                "AI chat timed out after %.0fs for user %s", _ANSWER_TIMEOUT, user_id
            )
            await _safe_edit(thinking_msg, str(M.AI_CHAT_OVERLOADED))
            return
        except ContentBlockedError:
            await _safe_edit(thinking_msg, str(M.AI_CHAT_BLOCKED))
            return
        except ServerError as e:
            if e.code == HTTPStatus.SERVICE_UNAVAILABLE:
                logger.warning("AI chat 503 overloaded for user %s", user_id)
                await _safe_edit(thinking_msg, str(M.AI_CHAT_OVERLOADED))
            else:
                logger.exception("AI chat server error for user %s", user_id)
                await _safe_edit(thinking_msg, str(M.AI_CHAT_ERROR))
            return
        except Exception:
            logger.exception("AI chat failed for user %s", user_id)
            await _safe_edit(thinking_msg, str(M.AI_CHAT_ERROR))
            return

        if len(answer) > _MAX_MESSAGE_LEN:
            answer = answer[: _MAX_MESSAGE_LEN - 1] + "…"

        history = history[-_HISTORY_KEEP:]
        history.append({"role": "user", "content": question})
        history.append({"role": "model", "content": answer})
        await state.update_data({UD_AI_CHAT_HISTORY: history})

        await _safe_edit(thinking_msg, answer)
