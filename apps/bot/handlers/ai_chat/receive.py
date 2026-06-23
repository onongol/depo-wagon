import asyncio
import logging

from google.genai.errors import ServerError
from telegram import Update
from telegram.ext import ContextTypes

from apps.ai_service.rag.chat import ContentBlockedError, answer_question
from apps.bot.constants import UD_AI_CHAT_HISTORY
from apps.bot.messages import BotMessages as M
from apps.bot.states import AI_CHAT

logger = logging.getLogger(__name__)

_HISTORY_KEEP = 4
_ANSWER_TIMEOUT = 60.0
_MAX_MESSAGE_LEN = 4096
_LOCK_KEY = "_ai_chat_lock"


async def _safe_edit(msg, text: str) -> None:
    try:
        await msg.edit_text(text)
    except Exception:
        pass


async def ai_chat_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive a user question, call the RAG-based answer generator, and reply with the answer."""
    question = update.message.text.strip()

    try:
        thinking_msg = await update.message.reply_text(str(M.AI_CHAT_THINKING))
    except Exception:
        logger.warning(
            "Could not send thinking message for user %s", update.effective_user.id
        )
        return AI_CHAT

    if _LOCK_KEY not in context.user_data:
        context.user_data[_LOCK_KEY] = asyncio.Lock()

    async with context.user_data[_LOCK_KEY]:
        history: list[dict] = context.user_data.get(UD_AI_CHAT_HISTORY, [])

        try:
            answer = await asyncio.wait_for(
                answer_question(question, history), timeout=_ANSWER_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(
                "AI chat timed out after %.0fs for user %s",
                _ANSWER_TIMEOUT,
                update.effective_user.id,
            )
            await _safe_edit(thinking_msg, str(M.AI_CHAT_OVERLOADED))
            return AI_CHAT
        except ContentBlockedError:
            await _safe_edit(thinking_msg, str(M.AI_CHAT_BLOCKED))
            return AI_CHAT
        except ServerError as e:
            if e.code == 503:
                logger.warning(
                    "AI chat 503 overloaded for user %s", update.effective_user.id
                )
                await _safe_edit(thinking_msg, str(M.AI_CHAT_OVERLOADED))
            else:
                logger.exception(
                    "AI chat server error for user %s", update.effective_user.id
                )
                await _safe_edit(thinking_msg, str(M.AI_CHAT_ERROR))
            return AI_CHAT
        except Exception:
            logger.exception("AI chat failed for user %s", update.effective_user.id)
            await _safe_edit(thinking_msg, str(M.AI_CHAT_ERROR))
            return AI_CHAT

        if len(answer) > _MAX_MESSAGE_LEN:
            answer = answer[: _MAX_MESSAGE_LEN - 1] + "…"

        history = history[-_HISTORY_KEEP:]
        history.append({"role": "user", "content": question})
        history.append({"role": "model", "content": answer})
        context.user_data[UD_AI_CHAT_HISTORY] = history

        await _safe_edit(thinking_msg, answer)
        return AI_CHAT
