from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramForbiddenError
from django.test import override_settings

from apps.bot.handlers.support import reply, request, start
from apps.bot.handlers.support.text import (
    build_support_ask_text,
    build_support_reply_blocked_text,
    build_support_reply_delivered_text,
    build_support_reply_header,
    build_support_reply_retry_text,
    build_support_request_text,
    build_support_request_unknown_text,
    build_support_sent_text,
    build_support_text_only_text,
    build_support_too_long_text,
    build_support_unavailable_text,
)
from apps.bot.handlers.support.utils import lookup_request, remember_request
from apps.bot.states import SupportSG
from apps.bot.tests.builders import make_message
from apps.bot.tests.storage import JSONMemoryStorage

BOT_ID = 42


def _make_user_message(text="My printer is broken"):
    """A private message from a user starting/continuing the /support flow."""
    message = make_message(text)
    message.from_user.id = 12345
    message.from_user.username = "basbish"
    message.from_user.full_name = "Bat Basbish"
    message.from_user.first_name = "Basbish"
    return message


def _make_group_reply(text="Your wagon is fixed", reply_to_id=100):
    """A reply inside the support group to a relayed request message."""
    message = make_message(text)
    message.message_id = 555
    message.chat.id = -1001234567890
    message.reply_to_message.message_id = reply_to_id
    return message


def _make_bot():
    return MagicMock(id=BOT_ID, send_message=AsyncMock(), copy_message=AsyncMock())


class TestSupportUnavailableText:
    @override_settings(TELEGRAM_SUPPORT_CONTACT="@helpdesk")
    def test_names_the_contact_at_the_end(self):
        assert (
            build_support_unavailable_text().as_kwargs()["text"].endswith(" @helpdesk")
        )

    @override_settings(TELEGRAM_SUPPORT_CONTACT="")
    def test_stands_without_a_contact(self):
        assert "@" not in build_support_unavailable_text().as_kwargs()["text"]


class TestSupportReply:
    async def test_ignores_when_not_a_reply(self):
        message = make_message()
        message.reply_to_message = None
        bot = _make_bot()

        with patch.object(reply, "lookup_request", AsyncMock()) as lookup:
            await reply.support_reply(message, bot, JSONMemoryStorage())

        lookup.assert_not_awaited()
        bot.send_message.assert_not_awaited()

    async def test_an_unknown_request_is_reported_to_the_operator(self):
        """The mapping expired, or the operator replied to the bot's own notice."""
        message = _make_group_reply()
        message.reply_to_message.from_user.id = BOT_ID
        bot = _make_bot()

        with patch.object(reply, "lookup_request", AsyncMock(return_value=None)):
            await reply.support_reply(message, bot, JSONMemoryStorage())

        bot.send_message.assert_not_awaited()
        bot.copy_message.assert_not_awaited()
        message.reply.assert_awaited_once_with(
            **build_support_request_unknown_text().as_kwargs()
        )

    async def test_a_reply_to_another_operator_is_left_alone(self):
        message = _make_group_reply()
        message.reply_to_message.from_user.id = 999
        bot = _make_bot()

        with patch.object(reply, "lookup_request", AsyncMock(return_value=None)):
            await reply.support_reply(message, bot, JSONMemoryStorage())

        bot.send_message.assert_not_awaited()
        message.reply.assert_not_awaited()

    async def test_the_reply_is_copied_under_the_header(self):
        """Copied rather than retyped, so the operator's links and markup survive."""
        message = _make_group_reply("see the instruction here")
        bot = _make_bot()

        with patch.object(reply, "lookup_request", AsyncMock(return_value=777)):
            await reply.support_reply(message, bot, JSONMemoryStorage())

        bot.send_message.assert_awaited_once_with(
            chat_id=777, **build_support_reply_header().as_kwargs()
        )
        bot.copy_message.assert_awaited_once_with(
            chat_id=777, from_chat_id=-1001234567890, message_id=555
        )
        message.reply.assert_awaited_once_with(
            **build_support_reply_delivered_text().as_kwargs()
        )

    async def test_a_blocked_user_is_named_as_the_reason(self):
        message = _make_group_reply("answer")
        bot = _make_bot()
        bot.send_message = AsyncMock(
            side_effect=TelegramForbiddenError(
                method=MagicMock(), message="Forbidden: bot was blocked by the user"
            )
        )

        with patch.object(reply, "lookup_request", AsyncMock(return_value=777)):
            await reply.support_reply(message, bot, JSONMemoryStorage())

        message.reply.assert_awaited_once_with(
            **build_support_reply_blocked_text().as_kwargs()
        )

    async def test_any_other_failure_asks_to_send_again(self):
        message = _make_group_reply("answer")
        bot = _make_bot()
        bot.copy_message = AsyncMock(side_effect=Exception("network down"))

        with patch.object(reply, "lookup_request", AsyncMock(return_value=777)):
            await reply.support_reply(message, bot, JSONMemoryStorage())

        message.reply.assert_awaited_once_with(
            **build_support_reply_retry_text().as_kwargs()
        )

    @pytest.mark.parametrize(
        "failure",
        [
            TelegramForbiddenError(method=MagicMock(), message="Forbidden"),
            Exception("network down"),
        ],
    )
    async def test_a_delivery_failure_logs_no_ids(self, caplog, failure):
        message = _make_group_reply("answer", reply_to_id=4242)
        bot = _make_bot()
        bot.send_message = AsyncMock(side_effect=failure)

        with patch.object(reply, "lookup_request", AsyncMock(return_value=777)):
            await reply.support_reply(message, bot, JSONMemoryStorage())

        assert "support reply" in caplog.text.lower()
        for identifier in ("4242", "777", "-1001234567890"):
            assert identifier not in caplog.text


class TestSupportStart:
    async def test_unavailable_when_not_configured(self, state):
        message = _make_user_message()

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=None):
            await start.support_start(message, state)

        assert await state.get_state() is None
        message.answer.assert_awaited_once_with(
            **build_support_unavailable_text().as_kwargs()
        )

    async def test_asks_question_when_configured(self, state):
        message = _make_user_message()

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=-100):
            await start.support_start(message, state)

        assert await state.get_state() == SupportSG.message.state
        message.answer.assert_awaited_once_with(**build_support_ask_text().as_kwargs())


class TestSupportReceive:
    async def test_relays_and_stores_mapping(self, state):
        message = _make_user_message("Printer broken")
        bot = _make_bot()
        sent = MagicMock()
        sent.message_id = 999
        bot.send_message = AsyncMock(return_value=sent)

        with (
            override_settings(TELEGRAM_SUPPORT_CHAT_ID=-100),
            patch.object(request, "remember_request", AsyncMock()) as remember,
        ):
            await request.support_receive(message, state, bot, None, state.storage)

        assert await state.get_state() is None
        # relayed to the support chat
        bot.send_message.assert_awaited_once()
        assert bot.send_message.call_args.kwargs["chat_id"] == -100
        # mapping stored: (relayed group message_id, asking user id)
        remember.assert_awaited_once_with(state.storage, -100, 999, 12345)
        # user gets the confirmation
        message.answer.assert_awaited_once_with(**build_support_sent_text().as_kwargs())

    async def test_the_request_names_the_employee_and_keeps_markup_literal(self, state):
        message = _make_user_message("  Is <b>this</b> bold?  ")
        bot = _make_bot()
        employee = MagicMock(full_name="Bat Erdene", employee_id="E-001")
        employee.get_role_display.return_value = "Inspector"

        with (
            override_settings(TELEGRAM_SUPPORT_CHAT_ID=-100),
            patch.object(request, "remember_request", AsyncMock()),
        ):
            await request.support_receive(message, state, bot, employee, state.storage)

        sent = bot.send_message.call_args.kwargs
        assert sent["parse_mode"] is None
        assert "👤 From: Bat Erdene (E-001, Inspector)" in sent["text"]
        assert "💬 @basbish" in sent["text"]
        assert sent["text"].endswith(
            "Question:\nIs <b>this</b> bold?\n\n"
            "↩️ Reply to this message to answer the user."
        )

    async def test_the_request_falls_back_to_the_telegram_name(self, state):
        message = _make_user_message()
        message.from_user.username = None
        bot = _make_bot()

        with (
            override_settings(TELEGRAM_SUPPORT_CHAT_ID=-100),
            patch.object(request, "remember_request", AsyncMock()),
        ):
            await request.support_receive(message, state, bot, None, state.storage)

        text = bot.send_message.call_args.kwargs["text"]
        assert "👤 From: Bat Basbish" in text
        assert "💬 —" in text

    async def test_a_failed_relay_logs_nothing_about_the_sender(self, state, caplog):
        message = _make_user_message()
        bot = _make_bot()
        bot.send_message = AsyncMock(side_effect=Exception("group gone"))
        employee = MagicMock(id=4711, full_name="Bat Erdene", employee_id="E-001")

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=-100):
            await request.support_receive(message, state, bot, employee, state.storage)

        assert "Failed to relay a support request" in caplog.text
        for personal in ("4711", "E-001", "12345", "Bat Erdene", "basbish"):
            assert personal not in caplog.text

    async def test_unavailable_when_not_configured(self, state):
        message = _make_user_message()
        bot = _make_bot()

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=None):
            await request.support_receive(message, state, bot, None, state.storage)

        assert await state.get_state() is None
        message.answer.assert_awaited_once_with(
            **build_support_unavailable_text().as_kwargs()
        )

    async def test_an_unstored_request_is_taken_back_from_the_group(
        self, state, caplog
    ):
        """A relayed question no reply can reach must not stay behind."""
        await state.set_state(SupportSG.message)
        message = _make_user_message()
        bot = _make_bot()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=999))
        bot.delete_message = AsyncMock()
        failing = AsyncMock(side_effect=ConnectionError("redis down"))

        with (
            override_settings(TELEGRAM_SUPPORT_CHAT_ID=-100),
            patch.object(request, "remember_request", failing),
        ):
            await request.support_receive(message, state, bot, None, state.storage)

        bot.delete_message.assert_awaited_once_with(chat_id=-100, message_id=999)
        message.answer.assert_awaited_once_with(
            **build_support_unavailable_text().as_kwargs()
        )
        assert await state.get_state() is None
        assert "Failed to store a support request" in caplog.text

    @pytest.mark.parametrize(
        ("question", "expected"),
        [
            ("   \n\t ", build_support_text_only_text),
            ("x" * 4096, build_support_too_long_text),
            # 2,100 characters, but 4,200 of the UTF-16 units Telegram counts
            ("🚃" * 2100, build_support_too_long_text),
        ],
        ids=["blank", "over-the-limit", "emoji-over-the-limit"],
    )
    async def test_a_question_that_cant_go_stays_in_the_dialog(
        self, state, question, expected
    ):
        await state.set_state(SupportSG.message)
        message = _make_user_message(question)
        bot = _make_bot()

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=-100):
            await request.support_receive(message, state, bot, None, state.storage)

        bot.send_message.assert_not_awaited()
        message.answer.assert_awaited_once_with(**expected().as_kwargs())
        assert await state.get_state() == SupportSG.message.state

    async def test_a_question_just_under_the_limit_is_relayed(self, state):
        heading = build_support_request_text("", _make_user_message().from_user, None)
        message = _make_user_message("x" * (4096 - len(heading)))
        bot = _make_bot()

        with (
            override_settings(TELEGRAM_SUPPORT_CHAT_ID=-100),
            patch.object(request, "remember_request", AsyncMock()),
        ):
            await request.support_receive(message, state, bot, None, state.storage)

        bot.send_message.assert_awaited_once()

    async def test_something_other_than_text_is_asked_again(self):
        message = _make_user_message(text=None)

        await request.support_not_text(message)

        message.answer.assert_awaited_once_with(
            **build_support_text_only_text().as_kwargs()
        )


class TestRequestMap:
    async def test_a_request_is_found_by_its_chat_and_message(self):
        storage = JSONMemoryStorage()
        await remember_request(storage, -100, 42, 777)

        assert await lookup_request(storage, -100, 42) == 777

    async def test_the_same_message_id_in_another_chat_is_unknown(self):
        storage = JSONMemoryStorage()
        await remember_request(storage, -100, 42, 777)

        assert await lookup_request(storage, -200, 42) is None


class TestSupportGroupRouter:
    """The reply half needs a concrete chat id to filter on."""

    def test_registers_the_reply_handler_when_a_chat_is_configured(self):
        from apps.bot.handlers.support.router import get_support_group_router

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=-1001234567890):
            router = get_support_group_router()

        callbacks = [h.callback.__name__ for h in router.message.handlers]
        assert callbacks == ["support_reply"]

    def test_is_empty_when_no_chat_is_configured(self):
        from apps.bot.handlers.support.router import get_support_group_router

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=None):
            router = get_support_group_router()

        assert router.message.handlers == []

    def test_a_private_chat_id_is_refused(self):
        """Behind the private tree, a person's replies would never reach it."""
        from apps.bot.handlers.support.router import get_support_group_router

        with (
            override_settings(TELEGRAM_SUPPORT_CHAT_ID=12345),
            pytest.raises(ValueError, match="TELEGRAM_SUPPORT_CHAT_ID"),
        ):
            get_support_group_router()

    def test_the_user_half_stands_without_a_chat(self):
        from apps.bot.handlers.support.router import get_support_router

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=None):
            router = get_support_router()

        callbacks = [h.callback.__name__ for h in router.message.handlers]
        assert "support_start" in callbacks
