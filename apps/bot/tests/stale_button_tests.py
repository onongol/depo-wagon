"""Tests for the callbacks nothing else claimed.

Two handlers, and the order between them is the whole design. The spacer is a
blank layout button on a live keyboard and has to stay silent — the regression
behind it is a tap on one replacing the employee list with "button expired".
Everything else reaching the unfiltered fallback is genuinely dead, so it is
told so rather than left spinning.
"""

import uuid

import pytest
from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import EditMessageText

from apps.bot.callback_data import CB_NOOP
from apps.bot.handlers.common.stale import noop_button, stale_button
from apps.bot.handlers.common.text import build_button_expired_text
from apps.bot.tests.builders import make_bad_request, make_callback


class TestNoopButton:
    async def test_answers_so_the_client_stops_spinning(self):
        callback = make_callback(CB_NOOP)

        await noop_button(callback)

        callback.answer.assert_awaited_once()

    async def test_leaves_the_message_alone(self):
        """A spacer tap must not disturb the list it sits in."""
        callback = make_callback(CB_NOOP)

        await noop_button(callback)

        callback.message.edit_text.assert_not_called()

    async def test_a_late_answer_is_not_an_error(self):
        """After downtime Telegram refuses the answer; nothing is left to do."""
        callback = make_callback(CB_NOOP)
        callback.answer.side_effect = make_bad_request("query is too old")

        await noop_button(callback)


class TestStaleButton:
    async def test_answers_the_query(self, bot):
        callback = make_callback(uuid.uuid4().hex)

        await stale_button(callback, bot)

        callback.answer.assert_awaited_once()

    async def test_replaces_the_message_with_an_explanation(self, bot):
        callback = make_callback(uuid.uuid4().hex)

        await stale_button(callback, bot)

        bot.edit_message_text.assert_awaited_once_with(
            **build_button_expired_text().as_kwargs(),
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
        )

    async def test_edits_through_the_bot_not_the_attached_message(self, bot):
        """callback.message may be inaccessible — this handler exists for old ones."""
        callback = make_callback(uuid.uuid4().hex)

        await stale_button(callback, bot)

        callback.message.edit_text.assert_not_called()

    async def test_an_uneditable_message_does_not_raise(self, bot):
        bot.edit_message_text.side_effect = make_bad_request(
            "message to edit not found"
        )

        await stale_button(make_callback(uuid.uuid4().hex), bot)

    async def test_still_answers_when_the_edit_fails(self, bot):
        bot.edit_message_text.side_effect = make_bad_request(
            "message to edit not found"
        )
        callback = make_callback(uuid.uuid4().hex)

        await stale_button(callback, bot)

        callback.answer.assert_awaited_once()

    async def test_a_late_answer_still_replaces_the_keyboard(self, bot):
        """After downtime Telegram refuses the answer; the edit must still happen."""
        callback = make_callback(uuid.uuid4().hex)
        callback.answer.side_effect = make_bad_request("query is too old")

        await stale_button(callback, bot)

        bot.edit_message_text.assert_awaited_once()

    async def test_a_failure_that_is_not_about_the_message_propagates(self, bot):
        """Only a 400 is expected here; the rest belongs to error_handler."""
        bot.edit_message_text.side_effect = TelegramRetryAfter(
            method=EditMessageText(chat_id=1, message_id=1, text="x"),
            message="Too Many Requests",
            retry_after=5,
        )

        with pytest.raises(TelegramRetryAfter):
            await stale_button(make_callback(uuid.uuid4().hex), bot)

    async def test_tolerates_a_missing_message(self, bot):
        callback = make_callback(uuid.uuid4().hex)
        callback.message = None

        await stale_button(callback, bot)

        callback.answer.assert_awaited_once()
        bot.edit_message_text.assert_not_called()
