import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.dispatcher.event.handler import HandlerObject
from aiogram.exceptions import TelegramNetworkError
from aiogram.utils.formatting import Text
from google.genai.errors import APIError, ClientError, ServerError

from apps.bot.constants import UD_AI_CHAT_HISTORY
from apps.bot.handlers.ai_chat.receive import ai_chat_not_text, ai_chat_receive
from apps.bot.handlers.ai_chat.start import ai_chat_start
from apps.bot.handlers.ai_chat.text import (
    build_ai_chat_blocked_text,
    build_ai_chat_error_text,
    build_ai_chat_greeting_text,
    build_ai_chat_overloaded_text,
    build_ai_chat_text_only_text,
    build_ai_chat_thinking_text,
)
from apps.bot.states import AiChatSG
from apps.bot.tests.builders import make_bad_request, make_message
from apps.bot.utils.unregistered import build_not_registered_text


def _make_employee():
    emp = MagicMock()
    emp.full_name = "Bat Erdene"
    emp.get_role_display.return_value = "Inspector"
    emp.role = "inspector"
    return emp


def _make_api_error(cls: type[APIError], code: int) -> APIError:
    return cls(code, {"error": {"code": code, "message": "err", "status": "ERR"}}, None)


class TestAiChatStart:
    def test_is_for_a_registered_chat_only(self):
        assert HandlerObject(callback=ai_chat_start).flags.get("registered")

    async def test_authenticated_returns_ai_chat_state(self, message, state):
        await ai_chat_start(message, state)

        assert await state.get_state() == AiChatSG.chatting.state

    async def test_clears_history_on_start(self, message, state):
        await state.update_data(
            {UD_AI_CHAT_HISTORY: [{"role": "user", "content": "old"}]}
        )
        await ai_chat_start(message, state)

        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == []

    async def test_sends_greeting(self, message, state):
        await ai_chat_start(message, state)

        message.answer.assert_called_once_with(
            **build_ai_chat_greeting_text().as_kwargs()
        )

    async def test_caches_employee_in_user_data(self, message, state):
        await ai_chat_start(message, state)

        assert UD_AI_CHAT_HISTORY in await state.get_data()

    async def test_greeting_send_failure_returns_end(self, message, state):
        message.answer = AsyncMock(
            side_effect=TelegramNetworkError(method=None, message="network")
        )
        await ai_chat_start(message, state)

        assert await state.get_state() is None


class TestAiChatReceive:
    async def _enter(self, state):
        """The router's StateFilter is what puts a real session here."""
        await state.set_state(AiChatSG.chatting)

    def _make_message(self, text="How to inspect a wheelset?"):
        message = make_message(text)
        thinking_msg = MagicMock()
        thinking_msg.edit_text = AsyncMock()
        thinking_msg.answer = AsyncMock()
        message.answer = AsyncMock(return_value=thinking_msg)
        return message, thinking_msg

    async def test_a_blank_question_is_asked_again_without_the_model(self, state):
        """Spaces that strip() removes but Telegram keeps as a message."""
        await self._enter(state)
        message, _ = self._make_message("\u00a0\u3000")
        answer = AsyncMock()

        with patch("apps.bot.handlers.ai_chat.receive.answer_question", answer):
            await ai_chat_receive(message, state, _make_employee())

        answer.assert_not_awaited()
        message.answer.assert_awaited_once_with(
            **build_ai_chat_text_only_text().as_kwargs()
        )
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_sends_thinking_message_first(self, state):
        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ответ"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        message.answer.assert_called_once_with(
            **build_ai_chat_thinking_text().as_kwargs()
        )

    async def test_edits_thinking_with_answer(self, state):
        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="Ответ депо"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_called_once_with(**Text("Ответ депо").as_kwargs())

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

    @pytest.mark.parametrize(
        ("error", "build_text", "traceback"),
        [
            (_make_api_error(ClientError, 429), build_ai_chat_overloaded_text, False),
            (_make_api_error(ServerError, 503), build_ai_chat_overloaded_text, False),
            (_make_api_error(ClientError, 400), build_ai_chat_error_text, True),
            (_make_api_error(ServerError, 500), build_ai_chat_error_text, True),
        ],
    )
    async def test_an_api_error_is_shown_by_whether_waiting_helps(
        self, state, caplog, error, build_text, traceback
    ):
        """A rate limit is not the question's fault: it is told to wait, not rephrase."""
        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=error),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_called_once_with(**build_text().as_kwargs())
        (record,) = caplog.records
        assert (record.exc_info is not None) is traceback
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_generic_exception_shows_error(self, state):
        await self._enter(state)
        message, thinking_msg = self._make_message()
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(side_effect=RuntimeError("unexpected")),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_called_once_with(
            **build_ai_chat_error_text().as_kwargs()
        )
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_a_failure_logs_neither_the_employee_nor_the_telegram_user(
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

        assert caplog.messages == ["AI chat failed"]

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

        thinking_msg.edit_text.assert_called_once_with(
            **build_ai_chat_blocked_text().as_kwargs()
        )
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

        thinking_msg.edit_text.assert_called_once_with(
            **build_ai_chat_overloaded_text().as_kwargs()
        )
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

    async def test_a_long_answer_goes_on_in_new_messages(self, state):
        await self._enter(state)
        await state.update_data({UD_AI_CHAT_HISTORY: []})
        message, thinking_msg = self._make_message()
        first, second = "А" * 3000, "Б" * 3000
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value=f"{first}\n{second}"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_awaited_once_with(**Text(first).as_kwargs())
        thinking_msg.answer.assert_awaited_once_with(**Text(second).as_kwargs())
        history = (await state.get_data())[UD_AI_CHAT_HISTORY]
        assert history[-1] == {"role": "model", "content": f"{first}\n{second}"}

    async def test_a_lost_piece_of_a_long_answer_is_not_remembered(self, state):
        await self._enter(state)
        await state.update_data({UD_AI_CHAT_HISTORY: []})
        message, thinking_msg = self._make_message()
        thinking_msg.answer = AsyncMock(
            side_effect=TelegramNetworkError(method=None, message="network")
        )
        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="А" * 3000 + "\n" + "Б" * 3000),
        ):
            await ai_chat_receive(message, state, _make_employee())

        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == []

    async def test_a_refused_edit_sends_the_answer_anew(self, state):
        await self._enter(state)
        await state.update_data({UD_AI_CHAT_HISTORY: []})
        message, thinking_msg = self._make_message()
        thinking_msg.edit_text = AsyncMock(
            side_effect=make_bad_request("Bad Request: message to edit not found")
        )

        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ok"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.answer.assert_awaited_once_with(**Text("ok").as_kwargs())
        assert len((await state.get_data())[UD_AI_CHAT_HISTORY]) == 2
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_an_edit_that_fails_otherwise_is_not_sent_anew(self, state):
        """A network error may hide an edit that went through."""
        await self._enter(state)
        message, thinking_msg = self._make_message()
        thinking_msg.edit_text = AsyncMock(
            side_effect=TelegramNetworkError(method=None, message="network")
        )

        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ok"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.answer.assert_not_awaited()

    async def test_an_undelivered_answer_is_not_remembered(self, state, caplog):
        await self._enter(state)
        await state.update_data({UD_AI_CHAT_HISTORY: []})
        message, thinking_msg = self._make_message()
        thinking_msg.edit_text = AsyncMock(
            side_effect=make_bad_request("Bad Request: message to edit not found")
        )
        thinking_msg.answer = AsyncMock(
            side_effect=TelegramNetworkError(method=None, message="network")
        )

        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value="ok"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == []
        assert "Could not show the AI chat reply" in caplog.text
        assert await state.get_state() == AiChatSG.chatting.state

    async def test_an_empty_answer_shows_the_error_and_is_not_remembered(self, state):
        """Telegram refuses an empty text, which left the placeholder up for good."""
        await self._enter(state)
        await state.update_data({UD_AI_CHAT_HISTORY: []})
        message, thinking_msg = self._make_message()

        with patch(
            "apps.bot.handlers.ai_chat.receive.answer_question",
            AsyncMock(return_value=" \n"),
        ):
            await ai_chat_receive(message, state, _make_employee())

        thinking_msg.edit_text.assert_called_once_with(
            **build_ai_chat_error_text().as_kwargs()
        )
        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == []

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


class TestAiChatNotText:
    async def test_asks_for_the_question_as_text(self):
        message = make_message()

        await ai_chat_not_text(message)

        message.answer.assert_awaited_once_with(
            **build_ai_chat_text_only_text().as_kwargs()
        )
