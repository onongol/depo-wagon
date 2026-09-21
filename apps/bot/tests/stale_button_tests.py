"""Tests for the callbacks nothing else claimed.

Two handlers, and the order between them is the whole design. The spacer is a
blank layout button on a live keyboard and has to stay silent — the regression
behind it is a tap on one replacing the employee list with "button expired".
Everything else reaching the unfiltered fallback is genuinely dead, so it is
told so rather than left spinning.
"""

import uuid

from apps.bot.callback_data import CB_NOOP
from apps.bot.handlers.common.stale import noop_button, stale_button
from apps.bot.messages import BotMessages as M
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


class TestStaleButton:
    async def test_answers_the_query(self, bot):
        callback = make_callback(uuid.uuid4().hex)

        await stale_button(callback, bot)

        callback.answer.assert_awaited_once()

    async def test_replaces_the_message_with_an_explanation(self, bot):
        callback = make_callback(uuid.uuid4().hex)

        await stale_button(callback, bot)

        bot.edit_message_text.assert_awaited_once_with(
            text=str(M.BUTTON_EXPIRED),
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

    async def test_tolerates_a_missing_message(self, bot):
        callback = make_callback(uuid.uuid4().hex)
        callback.message = None

        await stale_button(callback, bot)

        callback.answer.assert_awaited_once()
        bot.edit_message_text.assert_not_called()
