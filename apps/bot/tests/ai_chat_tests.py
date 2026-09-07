import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from google.genai.errors import ServerError
from telegram.error import NetworkError
from telegram.ext import ConversationHandler

from apps.bot.constants import UD_AI_CHAT_HISTORY
from apps.bot.handlers.ai_chat.receive import ai_chat_receive
from apps.bot.handlers.ai_chat.start import ai_chat_start
from apps.bot.messages import BotMessages as M
from apps.bot.states import AI_CHAT


def _make_employee():
    emp = MagicMock()
    emp.full_name = "Bat Erdene"
    emp.get_role_display.return_value = "Inspector"
    emp.role = "inspector"
    return emp


def _make_server_error(code: int) -> ServerError:
    return ServerError(
        code, {"error": {"code": code, "message": "err", "status": "ERR"}}, None
    )


class TestAiChatStart:
    async def test_unauthenticated_returns_end(self, mock_update, mock_context):
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee", AsyncMock(return_value=None)
        ):
            result = await ai_chat_start(mock_update, mock_context)

        assert result == ConversationHandler.END

    async def test_unauthenticated_sends_not_authenticated_message(
        self, mock_update, mock_context
    ):
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee", AsyncMock(return_value=None)
        ):
            await ai_chat_start(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            str(M.AI_CHAT_NOT_AUTHENTICATED)
        )

    async def test_authenticated_returns_ai_chat_state(self, mock_update, mock_context):
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(return_value=_make_employee()),
        ):
            result = await ai_chat_start(mock_update, mock_context)

        assert result == AI_CHAT

    async def test_clears_history_on_start(self, mock_update, mock_context):
        mock_context.user_data[UD_AI_CHAT_HISTORY] = [
            {"role": "user", "content": "old"}
        ]
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(return_value=_make_employee()),
        ):
            await ai_chat_start(mock_update, mock_context)

        assert mock_context.user_data[UD_AI_CHAT_HISTORY] == []

    async def test_sends_greeting_with_html_parse_mode(self, mock_update, mock_context):
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(return_value=_make_employee()),
        ):
            await ai_chat_start(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            str(M.AI_CHAT_GREETING), parse_mode=M.PARSE_MODE
        )

    async def test_caches_employee_in_user_data(self, mock_update, mock_context):
        employee = _make_employee()
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(return_value=employee),
        ):
            await ai_chat_start(mock_update, mock_context)

        # get_employee already writes to user_data internally; history key must exist
        assert UD_AI_CHAT_HISTORY in mock_context.user_data

    async def test_get_employee_exception_returns_end(self, mock_update, mock_context):
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(side_effect=RuntimeError("db down")),
        ):
            result = await ai_chat_start(mock_update, mock_context)

        assert result == ConversationHandler.END

    async def test_get_employee_exception_sends_no_message(
        self, mock_update, mock_context
    ):
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(side_effect=RuntimeError("db down")),
        ):
            await ai_chat_start(mock_update, mock_context)

        mock_update.message.reply_text.assert_not_called()

    async def test_greeting_send_failure_returns_end(self, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock(side_effect=NetworkError("network"))
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(return_value=_make_employee()),
        ):
            result = await ai_chat_start(mock_update, mock_context)

        assert result == ConversationHandler.END

    async def test_unauthenticated_reply_failure_still_returns_end(
        self, mock_update, mock_context
    ):
        mock_update.message.reply_text = AsyncMock(side_effect=NetworkError("network"))
        with patch(
            "apps.bot.handlers.ai_chat.start.get_employee",
            AsyncMock(return_value=None),
        ):
            result = await ai_chat_start(mock_update, mock_context)

        assert result == ConversationHandler.END


class TestAiChatReceive:
    def _make_update(self, text="How to inspect a wheelset?"):
        update = MagicMock()
        update.message.text = text
        update.effective_user.id = 12345
        thinking_msg = MagicMock()
        thinking_msg.edit_text = AsyncMock()
        update.message.reply_text = AsyncMock(return_value=thinking_msg)
        return update, thinking_msg

    async def test_sends_thinking_message_first(self, mock_context):
        update, thinking_msg = self._make_update()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ответ"),
        ):
            await ai_chat_receive(update, mock_context)

        update.message.reply_text.assert_called_once_with(str(M.AI_CHAT_THINKING))

    async def test_edits_thinking_with_answer(self, mock_context):
        update, thinking_msg = self._make_update()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="Ответ депо"),
        ):
            await ai_chat_receive(update, mock_context)

        thinking_msg.edit_text.assert_called_once_with("Ответ депо")

    async def test_stays_in_ai_chat_on_success(self, mock_context):
        update, _ = self._make_update()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ok"),
        ):
            result = await ai_chat_receive(update, mock_context)

        assert result == AI_CHAT

    async def test_appends_question_and_answer_to_history(self, mock_context):
        update, _ = self._make_update("question about axle")
        mock_context.user_data[UD_AI_CHAT_HISTORY] = []
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="answer about axle"),
        ):
            await ai_chat_receive(update, mock_context)

        history = mock_context.user_data[UD_AI_CHAT_HISTORY]
        assert {"role": "user", "content": "question about axle"} in history
        assert {"role": "model", "content": "answer about axle"} in history

    async def test_history_grows_by_two_per_turn(self, mock_context):
        update, _ = self._make_update()
        mock_context.user_data[UD_AI_CHAT_HISTORY] = [
            {"role": "user", "content": "q1"},
            {"role": "model", "content": "a1"},
        ]
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="a2"),
        ):
            await ai_chat_receive(update, mock_context)

        assert len(mock_context.user_data[UD_AI_CHAT_HISTORY]) == 4

    async def test_history_capped_before_appending(self, mock_context):
        from apps.bot.handlers.ai_chat.receive import _HISTORY_KEEP

        update, _ = self._make_update()
        mock_context.user_data[UD_AI_CHAT_HISTORY] = [
            {"role": "user" if i % 2 == 0 else "model", "content": f"old {i}"}
            for i in range(_HISTORY_KEEP + 6)
        ]
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="new"),
        ):
            await ai_chat_receive(update, mock_context)

        history = mock_context.user_data[UD_AI_CHAT_HISTORY]
        assert len(history) <= _HISTORY_KEEP + 2

    async def test_503_error_shows_overloaded_message(self, mock_context):
        update, thinking_msg = self._make_update()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=_make_server_error(503)),
        ):
            result = await ai_chat_receive(update, mock_context)

        thinking_msg.edit_text.assert_called_once_with(str(M.AI_CHAT_OVERLOADED))
        assert result == AI_CHAT

    async def test_other_server_error_shows_generic_error(self, mock_context):
        update, thinking_msg = self._make_update()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=_make_server_error(500)),
        ):
            result = await ai_chat_receive(update, mock_context)

        thinking_msg.edit_text.assert_called_once_with(str(M.AI_CHAT_ERROR))
        assert result == AI_CHAT

    async def test_generic_exception_shows_error(self, mock_context):
        update, thinking_msg = self._make_update()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=RuntimeError("unexpected")),
        ):
            result = await ai_chat_receive(update, mock_context)

        thinking_msg.edit_text.assert_called_once_with(str(M.AI_CHAT_ERROR))
        assert result == AI_CHAT

    async def test_error_does_not_update_history(self, mock_context):
        update, _ = self._make_update()
        mock_context.user_data[UD_AI_CHAT_HISTORY] = []
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=RuntimeError("fail")),
        ):
            await ai_chat_receive(update, mock_context)

        assert mock_context.user_data[UD_AI_CHAT_HISTORY] == []

    async def test_content_blocked_shows_blocked_message(self, mock_context):
        from apps.ai_service.rag.chat import ContentBlockedError

        update, thinking_msg = self._make_update()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=ContentBlockedError()),
        ):
            result = await ai_chat_receive(update, mock_context)

        thinking_msg.edit_text.assert_called_once_with(str(M.AI_CHAT_BLOCKED))
        assert result == AI_CHAT

    async def test_content_blocked_does_not_update_history(self, mock_context):
        from apps.ai_service.rag.chat import ContentBlockedError

        update, _ = self._make_update()
        mock_context.user_data[UD_AI_CHAT_HISTORY] = []
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=ContentBlockedError()),
        ):
            await ai_chat_receive(update, mock_context)

        assert mock_context.user_data[UD_AI_CHAT_HISTORY] == []

    async def test_passes_existing_history_to_answer_question(self, mock_context):
        update, _ = self._make_update("new question")
        existing = [
            {"role": "user", "content": "previous question"},
            {"role": "model", "content": "previous answer"},
        ]
        mock_context.user_data[UD_AI_CHAT_HISTORY] = list(existing)
        answer_mock = AsyncMock(return_value="ok")

        with patch("apps.bot.handlers.ai_chat.receive.answer_question", answer_mock):
            await ai_chat_receive(update, mock_context)

        answer_mock.assert_awaited_once()
        _, call_history = answer_mock.call_args.args
        assert call_history == existing

    async def test_timeout_shows_overloaded_message(self, mock_context):
        update, thinking_msg = self._make_update()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            result = await ai_chat_receive(update, mock_context)

        thinking_msg.edit_text.assert_called_once_with(str(M.AI_CHAT_OVERLOADED))
        assert result == AI_CHAT

    async def test_timeout_does_not_update_history(self, mock_context):
        update, _ = self._make_update()
        mock_context.user_data[UD_AI_CHAT_HISTORY] = []
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            await ai_chat_receive(update, mock_context)

        assert mock_context.user_data[UD_AI_CHAT_HISTORY] == []

    async def test_thinking_send_failure_returns_ai_chat(self, mock_context):
        update, _ = self._make_update()
        update.message.reply_text = AsyncMock(side_effect=NetworkError("network"))

        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ok"),
        ):
            result = await ai_chat_receive(update, mock_context)

        assert result == AI_CHAT

    async def test_thinking_send_failure_skips_answer_question(self, mock_context):
        update, _ = self._make_update()
        update.message.reply_text = AsyncMock(side_effect=NetworkError("network"))
        answer_mock = AsyncMock(return_value="ok")

        with patch("apps.bot.handlers.ai_chat.receive.answer_question", answer_mock):
            await ai_chat_receive(update, mock_context)

        answer_mock.assert_not_awaited()

    async def test_long_answer_is_truncated_to_max_len(self, mock_context):
        from apps.bot.handlers.ai_chat.receive import _MAX_MESSAGE_LEN

        update, thinking_msg = self._make_update()
        long_answer = "А" * (_MAX_MESSAGE_LEN + 100)
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value=long_answer),
        ):
            await ai_chat_receive(update, mock_context)

        edited_text = thinking_msg.edit_text.call_args.args[0]
        assert len(edited_text) <= _MAX_MESSAGE_LEN
        assert edited_text.endswith("…")

    async def test_deleted_thinking_message_does_not_raise(self, mock_context):
        from telegram.error import BadRequest

        update, thinking_msg = self._make_update()
        thinking_msg.edit_text = AsyncMock(
            side_effect=BadRequest("Message to edit not found")
        )

        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ok"),
        ):
            result = await ai_chat_receive(update, mock_context)

        assert result == AI_CHAT
