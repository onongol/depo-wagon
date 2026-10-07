from unittest.mock import AsyncMock, MagicMock, patch

from django.test import override_settings

from apps.bot.handlers.support import reply, request, start
from apps.bot.handlers.support.text import (
    build_support_ask_text,
    build_support_reply_delivered_text,
    build_support_reply_failed_text,
    build_support_reply_header,
    build_support_reply_text,
    build_support_sent_text,
    build_support_unavailable_text,
)
from apps.bot.handlers.support.utils import support_chat_id
from apps.bot.states import SupportSG
from apps.bot.tests.builders import make_message


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
    return MagicMock(send_message=AsyncMock(), copy_message=AsyncMock())


class TestSupportChatId:
    @override_settings(TELEGRAM_SUPPORT_CHAT_ID="-1001234567890")
    def test_valid_returns_int(self):
        assert support_chat_id() == -1001234567890

    @override_settings(TELEGRAM_SUPPORT_CHAT_ID="")
    def test_empty_returns_none(self):
        assert support_chat_id() is None

    @override_settings(TELEGRAM_SUPPORT_CHAT_ID="not-a-number")
    def test_garbage_returns_none(self):
        assert support_chat_id() is None


class TestSupportReply:
    async def test_ignores_when_not_a_reply(self):
        message = make_message()
        message.reply_to_message = None
        bot = _make_bot()

        with patch.object(reply, "lookup_request", AsyncMock()) as lookup:
            await reply.support_reply(message, bot)

        lookup.assert_not_awaited()
        bot.send_message.assert_not_awaited()

    async def test_ignores_when_mapping_missing(self):
        message = _make_group_reply()
        bot = _make_bot()

        with patch.object(reply, "lookup_request", AsyncMock(return_value=None)):
            await reply.support_reply(message, bot)

        bot.send_message.assert_not_awaited()
        bot.copy_message.assert_not_awaited()

    async def test_text_reply_delivered_to_user(self):
        message = _make_group_reply("<b>Your</b> wagon is fixed")
        bot = _make_bot()

        with patch.object(reply, "lookup_request", AsyncMock(return_value=777)):
            await reply.support_reply(message, bot)

        bot.send_message.assert_awaited_once_with(
            chat_id=777,
            **build_support_reply_text("<b>Your</b> wagon is fixed").as_kwargs(),
        )
        bot.copy_message.assert_not_awaited()
        message.reply.assert_awaited_once_with(
            **build_support_reply_delivered_text().as_kwargs()
        )

    async def test_media_reply_uses_copy_message(self):
        message = _make_group_reply(text=None)  # non-text (photo / sticker / voice)
        bot = _make_bot()

        with patch.object(reply, "lookup_request", AsyncMock(return_value=777)):
            await reply.support_reply(message, bot)

        # header sent + original content copied to the user
        bot.send_message.assert_awaited_once_with(
            chat_id=777, **build_support_reply_header().as_kwargs()
        )
        bot.copy_message.assert_awaited_once()
        assert bot.copy_message.call_args.kwargs["chat_id"] == 777
        message.reply.assert_awaited_once_with(
            **build_support_reply_delivered_text().as_kwargs()
        )

    async def test_delivery_failure_notifies_support(self):
        message = _make_group_reply("answer")
        bot = _make_bot()
        bot.send_message = AsyncMock(side_effect=Exception("blocked"))

        with patch.object(reply, "lookup_request", AsyncMock(return_value=777)):
            await reply.support_reply(message, bot)

        message.reply.assert_awaited_once_with(
            **build_support_reply_failed_text().as_kwargs()
        )

    async def test_a_delivery_failure_logs_the_request_not_the_user(self, caplog):
        message = _make_group_reply("answer", reply_to_id=4242)
        bot = _make_bot()
        bot.send_message = AsyncMock(side_effect=Exception("blocked"))

        with patch.object(reply, "lookup_request", AsyncMock(return_value=777)):
            await reply.support_reply(message, bot)

        assert "request 4242" in caplog.text
        assert "777" not in caplog.text


class TestSupportStart:
    async def test_unavailable_when_not_configured(self, state):
        message = _make_user_message()

        with patch.object(start, "support_chat_id", return_value=None):
            await start.support_start(message, state)

        assert await state.get_state() is None
        message.answer.assert_awaited_once_with(
            **build_support_unavailable_text().as_kwargs()
        )

    async def test_asks_question_when_configured(self, state):
        message = _make_user_message()

        with patch.object(start, "support_chat_id", return_value=-100):
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
            patch.object(request, "support_chat_id", return_value=-100),
            patch.object(request, "remember_request", AsyncMock()) as remember,
        ):
            await request.support_receive(message, state, bot, None)

        assert await state.get_state() is None
        # relayed to the support chat
        bot.send_message.assert_awaited_once()
        assert bot.send_message.call_args.kwargs["chat_id"] == -100
        # mapping stored: (relayed group message_id, asking user id)
        remember.assert_awaited_once_with(999, 12345)
        # user gets the confirmation
        message.answer.assert_awaited_once_with(**build_support_sent_text().as_kwargs())

    async def test_the_request_names_the_employee_and_keeps_markup_literal(self, state):
        message = _make_user_message("  Is <b>this</b> bold?  ")
        bot = _make_bot()
        employee = MagicMock(full_name="Bat Erdene", employee_id="E-001")
        employee.get_role_display.return_value = "Inspector"

        with (
            patch.object(request, "support_chat_id", return_value=-100),
            patch.object(request, "remember_request", AsyncMock()),
        ):
            await request.support_receive(message, state, bot, employee)

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
            patch.object(request, "support_chat_id", return_value=-100),
            patch.object(request, "remember_request", AsyncMock()),
        ):
            await request.support_receive(message, state, bot, None)

        text = bot.send_message.call_args.kwargs["text"]
        assert "👤 From: Bat Basbish" in text
        assert "💬 —" in text

    async def test_a_failed_relay_logs_the_employee_not_the_telegram_user(
        self, state, caplog
    ):
        message = _make_user_message()
        bot = _make_bot()
        bot.send_message = AsyncMock(side_effect=Exception("group gone"))
        employee = MagicMock(id=7, full_name="Bat Erdene", employee_id="E-001")

        with patch.object(request, "support_chat_id", return_value=-100):
            await request.support_receive(message, state, bot, employee)

        assert "employee 7" in caplog.text
        for personal in ("12345", "Bat Erdene", "basbish"):
            assert personal not in caplog.text

    async def test_a_failed_relay_from_an_unlinked_chat_logs_no_id(self, state, caplog):
        message = _make_user_message()
        bot = _make_bot()
        bot.send_message = AsyncMock(side_effect=Exception("group gone"))

        with patch.object(request, "support_chat_id", return_value=-100):
            await request.support_receive(message, state, bot, None)

        assert "an unlinked chat" in caplog.text
        assert "12345" not in caplog.text

    async def test_unavailable_when_not_configured(self, state):
        message = _make_user_message()
        bot = _make_bot()

        with patch.object(request, "support_chat_id", return_value=None):
            await request.support_receive(message, state, bot, None)

        assert await state.get_state() is None
        message.answer.assert_awaited_once_with(
            **build_support_unavailable_text().as_kwargs()
        )


class TestSupportGroupRouter:
    """The reply half needs a concrete chat id to filter on."""

    def test_registers_the_reply_handler_when_a_chat_is_configured(self):
        from apps.bot.handlers.support.router import get_support_group_router

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID="-1001234567890"):
            router = get_support_group_router()

        callbacks = [h.callback.__name__ for h in router.message.handlers]
        assert callbacks == ["support_reply"]

    def test_is_empty_when_no_chat_is_configured(self):
        from apps.bot.handlers.support.router import get_support_group_router

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=""):
            router = get_support_group_router()

        assert router.message.handlers == []

    def test_the_user_half_stands_without_a_chat(self):
        from apps.bot.handlers.support.router import get_support_router

        with override_settings(TELEGRAM_SUPPORT_CHAT_ID=""):
            router = get_support_router()

        callbacks = [h.callback.__name__ for h in router.message.handlers]
        assert "support_start" in callbacks
