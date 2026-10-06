import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.dispatcher.event.handler import HandlerObject
from aiogram.exceptions import TelegramNetworkError
from google.genai.errors import ServerError

from apps.bot.constants import UD_AI_CHAT_HISTORY
from apps.bot.handlers.ai_chat.receive import ai_chat_receive
from apps.bot.handlers.ai_chat.start import ai_chat_start
from apps.bot.messages import BotMessages as M
from apps.bot.states import AiChatSG
from apps.bot.tests.builders import make_bad_request, make_message
from apps.bot.utils.unregistered import build_not_registered_text


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
    def test_is_for_a_registered_chat_only(self):
        assert HandlerObject(callback=ai_chat_start).flags.get("registered")

    async def test_authenticated_returns_ai_chat_state(self, message, state):
        await ai_chat_start(message, state, _make_employee())

        assert await state.get_state() == AiChatSG.chatting.state

    async def test_clears_history_on_start(self, message, state):
        await state.update_data(
            {UD_AI_CHAT_HISTORY: [{"role": "user", "content": "old"}]}
        )
        await ai_chat_start(message, state, _make_employee())

        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == []

    async def test_sends_greeting_with_html_parse_mode(self, message, state):
        await ai_chat_start(message, state, _make_employee())

        message.answer.assert_called_once_with(
            str(M.AI_CHAT_GREETING), parse_mode=M.PARSE_MODE
        )

    async def test_caches_employee_in_user_data(self, message, state):
        await ai_chat_start(message, state, _make_employee())

        assert UD_AI_CHAT_HISTORY in await state.get_data()

    async def test_greeting_send_failure_returns_end(self, message, state):
        message.answer = AsyncMock(
            side_effect=TelegramNetworkError(method=None, message="network")
        )
        await ai_chat_start(message, state, _make_employee())

        assert await state.get_state() is None


class TestAiChatReceive:
    async def _enter(self, state):
        """The router's StateFilter is what puts a real session here."""
        await state.set_state(AiChatSG.chatting)

    def _make_message(self, text="How to inspect a wheelset?"):
        message = make_message(text)
        thinking_msg = MagicMock()
        thinking_msg.edit_text = AsyncMock()
        message.answer = AsyncMock(return_value=thinking_msg)
        return message, thinking_msg

    async def test_sends_thinking_message_first(self, state):
        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ответ"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        message.answer.assert_called_once_with(str(M.AI_CHAT_THINKING))

    async def test_edits_thinking_with_answer(self, state):
        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="Ответ депо"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_called_once_with("Ответ депо")

    async def test_stays_in_ai_chat_on_success(self, state):
        await self._enter(state)
        message, _ = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ok"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        assert await state.get_state() == AiChatSG.chatting.state

    async def test_appends_question_and_answer_to_history(self, state):
        await self._enter(state)
        message, _ = self._make_message("question about axle")
        await state.update_data({UD_AI_CHAT_HISTORY: []})
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="answer about axle"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        history = (await state.get_data())[UD_AI_CHAT_HISTORY]
        assert {"role": "user", "content": "question about axle"} in history
        assert {"role": "model", "content": "answer about axle"} in history

    async def test_history_grows_by_two_per_turn(self, state):
        await self._enter(state)
        message, _ = self._make_message()
        await state.update_data(
            {
                UD_AI_CHAT_HISTORY: [
                    {"role": "user", "content": "q1"},
                    {"role": "model", "content": "a1"},
                ]
            }
        )
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="a2"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        assert len((await state.get_data())[UD_AI_CHAT_HISTORY]) == 4

    async def test_history_capped_before_appending(self, state):
        from apps.bot.handlers.ai_chat.receive import _HISTORY_KEEP

        message, _ = self._make_message()
        await state.update_data(
            {
                UD_AI_CHAT_HISTORY: [
                    {"role": "user" if i % 2 == 0 else "model", "content": f"old {i}"}
                    for i in range(_HISTORY_KEEP + 6)
                ]
            }
        )
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="new"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        history = (await state.get_data())[UD_AI_CHAT_HISTORY]
        assert len(history) <= _HISTORY_KEEP + 2

    async def test_503_error_shows_overloaded_message(self, state):
        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=_make_server_error(503)),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_called_once_with(str(M.AI_CHAT_OVERLOADED))
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_other_server_error_shows_generic_error(self, state):
        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=_make_server_error(500)),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_called_once_with(str(M.AI_CHAT_ERROR))
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_generic_exception_shows_error(self, state):
        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=RuntimeError("unexpected")),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_called_once_with(str(M.AI_CHAT_ERROR))
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_a_failure_logs_the_employee_not_the_telegram_user(
        self, state, caplog
    ):
        await self._enter(state)
        message, _ = self._make_message()
        employee = _make_employee()
        employee.id = 7
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=RuntimeError("unexpected")),
        ):
            await ai_chat_receive(message, state, employee)

        assert "employee 7" in caplog.text
        assert str(message.from_user.id) not in caplog.text

    async def test_error_does_not_update_history(self, state):
        await self._enter(state)
        message, _ = self._make_message()
        await state.update_data({UD_AI_CHAT_HISTORY: []})
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=RuntimeError("fail")),
        ):
            await ai_chat_receive(message, state, _make_employee())

        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == []

    async def test_content_blocked_shows_blocked_message(self, state):
        from apps.ai_service.rag.chat import ContentBlockedError

        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=ContentBlockedError()),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_called_once_with(str(M.AI_CHAT_BLOCKED))
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_content_blocked_does_not_update_history(self, state):
        from apps.ai_service.rag.chat import ContentBlockedError

        message, _ = self._make_message()
        await state.update_data({UD_AI_CHAT_HISTORY: []})
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=ContentBlockedError()),
        ):
            await ai_chat_receive(message, state, _make_employee())

        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == []

    async def test_passes_existing_history_to_answer_question(self, state):
        await self._enter(state)
        message, _ = self._make_message("new question")
        existing = [
            {"role": "user", "content": "previous question"},
            {"role": "model", "content": "previous answer"},
        ]
        await state.update_data({UD_AI_CHAT_HISTORY: list(existing)})
        answer_mock = AsyncMock(return_value="ok")

        with patch("apps.bot.handlers.ai_chat.receive.answer_question", answer_mock):
            await ai_chat_receive(message, state, _make_employee())

        answer_mock.assert_awaited_once()
        _, call_history = answer_mock.call_args.args
        assert call_history == existing

    async def test_timeout_shows_overloaded_message(self, state):
        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_called_once_with(str(M.AI_CHAT_OVERLOADED))
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_timeout_does_not_update_history(self, state):
        await self._enter(state)
        message, _ = self._make_message()
        await state.update_data({UD_AI_CHAT_HISTORY: []})
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            await ai_chat_receive(message, state, _make_employee())

        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == []

    async def test_thinking_send_failure_returns_ai_chat(self, state):
        await self._enter(state)
        message, _ = self._make_message()
        message.answer = AsyncMock(
            side_effect=TelegramNetworkError(method=None, message="network")
        )

        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ok"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        assert await state.get_state() == AiChatSG.chatting.state

    async def test_thinking_send_failure_skips_answer_question(self, state):
        await self._enter(state)
        message, _ = self._make_message()
        message.answer = AsyncMock(
            side_effect=TelegramNetworkError(method=None, message="network")
        )
        answer_mock = AsyncMock(return_value="ok")

        with patch("apps.bot.handlers.ai_chat.receive.answer_question", answer_mock):
            await ai_chat_receive(message, state, _make_employee())

        answer_mock.assert_not_awaited()

    async def test_long_answer_is_truncated_to_max_len(self, state):
        from apps.bot.handlers.ai_chat.receive import _MAX_MESSAGE_LEN

        message, thinking_msg = self._make_message()
        long_answer = "А" * (_MAX_MESSAGE_LEN + 100)
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value=long_answer),
        ):
            await ai_chat_receive(message, state, _make_employee())

        edited_text = thinking_msg.edit_text.call_args.args[0]
        assert len(edited_text) <= _MAX_MESSAGE_LEN
        assert edited_text.endswith("…")

    async def test_deleted_thinking_message_does_not_raise(self, state):
        await self._enter(state)
        message, thinking_msg = self._make_message()
        thinking_msg.edit_text = AsyncMock(
            side_effect=make_bad_request("Bad Request: message to edit not found")
        )

        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ok"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        assert await state.get_state() == AiChatSG.chatting.state

    async def test_a_lost_employee_ends_the_session_without_asking(self, state):
        """Deactivated or unlinked on the web while the session was open."""
        await self._enter(state)
        await state.update_data({UD_AI_CHAT_HISTORY: [{"role": "user"}]})
        message, _ = self._make_message()
        answer = AsyncMock()

        with patch("apps.bot.handlers.ai_chat.receive.answer_question", answer):
            await ai_chat_receive(message, state, None)

        answer.assert_not_awaited()
        message.answer.assert_awaited_once_with(
            **build_not_registered_text().as_kwargs()
        )
        assert await state.get_state() is None
        assert await state.get_data() == {}

    async def test_a_lost_employee_is_ended_even_if_the_reply_fails(self, state):
        await self._enter(state)
        message, _ = self._make_message()
        message.answer = AsyncMock(
            side_effect=TelegramNetworkError(method=None, message="network")
        )

        await ai_chat_receive(message, state, None)

        assert await state.get_state() is None
