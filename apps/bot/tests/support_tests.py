from unittest.mock import AsyncMock, MagicMock, patch

from django.test import override_settings
from telegram.ext import ConversationHandler

from apps.bot.handlers.support import admin_handlers, user_handlers
from apps.bot.handlers.support.utils import support_chat_id
from apps.bot.messages import BotMessages as M
from apps.bot.states import SUPPORT_MESSAGE


def _make_context():
    context = MagicMock()
    context.user_data = {}
    context.bot = AsyncMock()
    return context


def _make_user_update(text="My printer is broken"):
    """A private message from a user starting/continuing the /support flow."""
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.effective_user.id = 12345
    update.effective_user.username = "basbish"
    update.effective_user.full_name = "Bat Basbish"
    update.effective_user.first_name = "Basbish"
    return update


def _make_group_reply(text="Your wagon is fixed", reply_to_id=100):
    """A reply inside the support group to a relayed request message."""
    update = MagicMock()
    update.message.text = text
    update.message.message_id = 555
    update.message.chat_id = -1001234567890
    update.message.reply_text = AsyncMock()
    update.message.reply_to_message.message_id = reply_to_id
    return update


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
        update = MagicMock()
        update.message.reply_to_message = None
        context = _make_context()

        with patch.object(admin_handlers, "lookup_request", AsyncMock()) as lookup:
            await admin_handlers.support_reply(update, context)

        lookup.assert_not_awaited()
        context.bot.send_message.assert_not_awaited()

    async def test_ignores_when_mapping_missing(self):
        update = _make_group_reply()
        context = _make_context()

        with patch.object(
            admin_handlers, "lookup_request", AsyncMock(return_value=None)
        ):
            await admin_handlers.support_reply(update, context)

        context.bot.send_message.assert_not_awaited()
        context.bot.copy_message.assert_not_awaited()

    async def test_text_reply_delivered_to_user(self):
        update = _make_group_reply("Your wagon is fixed")
        context = _make_context()

        with patch.object(
            admin_handlers, "lookup_request", AsyncMock(return_value=777)
        ):
            await admin_handlers.support_reply(update, context)

        context.bot.send_message.assert_awaited_once()
        assert context.bot.send_message.call_args.kwargs["chat_id"] == 777
        context.bot.copy_message.assert_not_awaited()
        update.message.reply_text.assert_awaited_once_with(
            str(M.SUPPORT_REPLY_DELIVERED)
        )

    async def test_media_reply_uses_copy_message(self):
        update = _make_group_reply(text=None)  # non-text (photo / sticker / voice)
        context = _make_context()

        with patch.object(
            admin_handlers, "lookup_request", AsyncMock(return_value=777)
        ):
            await admin_handlers.support_reply(update, context)

        # header sent + original content copied to the user
        context.bot.send_message.assert_awaited_once()
        context.bot.copy_message.assert_awaited_once()
        assert context.bot.copy_message.call_args.kwargs["chat_id"] == 777
        update.message.reply_text.assert_awaited_once_with(
            str(M.SUPPORT_REPLY_DELIVERED)
        )

    async def test_delivery_failure_notifies_support(self):
        update = _make_group_reply("answer")
        context = _make_context()
        context.bot.send_message = AsyncMock(side_effect=Exception("blocked"))

        with patch.object(
            admin_handlers, "lookup_request", AsyncMock(return_value=777)
        ):
            await admin_handlers.support_reply(update, context)

        update.message.reply_text.assert_awaited_once_with(str(M.SUPPORT_REPLY_FAILED))


class TestSupportStart:
    async def test_unavailable_when_not_configured(self):
        update = _make_user_update()
        context = _make_context()

        with patch.object(user_handlers, "support_chat_id", return_value=None):
            result = await user_handlers.support_start(update, context)

        assert result == ConversationHandler.END
        update.message.reply_text.assert_awaited_once_with(
            str(M.SUPPORT_UNAVAILABLE), parse_mode=M.PARSE_MODE
        )

    async def test_asks_question_when_configured(self):
        update = _make_user_update()
        context = _make_context()

        with patch.object(user_handlers, "support_chat_id", return_value=-100):
            result = await user_handlers.support_start(update, context)

        assert result == SUPPORT_MESSAGE
        update.message.reply_text.assert_awaited_once_with(
            str(M.SUPPORT_ASK), parse_mode=M.PARSE_MODE
        )


class TestSupportReceive:
    async def test_relays_and_stores_mapping(self):
        update = _make_user_update("Printer broken")
        context = _make_context()
        sent = MagicMock()
        sent.message_id = 999
        context.bot.send_message = AsyncMock(return_value=sent)

        with (
            patch.object(user_handlers, "support_chat_id", return_value=-100),
            patch.object(user_handlers, "get_employee", AsyncMock(return_value=None)),
            patch.object(user_handlers, "remember_request", AsyncMock()) as remember,
        ):
            result = await user_handlers.support_receive(update, context)

        assert result == ConversationHandler.END
        # relayed to the support chat
        context.bot.send_message.assert_awaited_once()
        assert context.bot.send_message.call_args.kwargs["chat_id"] == -100
        # mapping stored: (relayed group message_id, asking user id)
        remember.assert_awaited_once_with(999, 12345)
        # user gets the confirmation
        update.message.reply_text.assert_awaited_once_with(str(M.SUPPORT_SENT))

    async def test_unavailable_when_not_configured(self):
        update = _make_user_update()
        context = _make_context()

        with patch.object(user_handlers, "support_chat_id", return_value=None):
            result = await user_handlers.support_receive(update, context)

        assert result == ConversationHandler.END
        update.message.reply_text.assert_awaited_once_with(
            str(M.SUPPORT_UNAVAILABLE), parse_mode=M.PARSE_MODE
        )
