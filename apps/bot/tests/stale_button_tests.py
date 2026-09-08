"""Tests for the callbacks nothing else claimed.

PTB had two behaviours — silent inside the defect conversation, loud outside —
and the split into three tiers has to preserve both. The spacer tier is the one
with a user-visible regression behind it: a blank layout button that fell
through to the loud tier would replace the employee list with "button expired".
"""

import uuid

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText

from apps.bot.callback_data import CB_NOOP, DepartmentCB, is_known_callback
from apps.bot.handlers.common.stale import (
    noop_button,
    stale_button,
    unroutable_button,
)
from apps.bot.messages import BotMessages as M
from apps.bot.tests.builders import make_callback


def _bad_request(message: str) -> TelegramBadRequest:
    return TelegramBadRequest(
        method=EditMessageText(chat_id=1, message_id=1, text="x"), message=message
    )


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


class TestUnroutableButton:
    async def test_absorbs_a_valid_payload_silently(self):
        callback = make_callback(DepartmentCB(value="bogie").pack())

        await unroutable_button(callback)

        callback.answer.assert_awaited_once()
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
        bot.edit_message_text.side_effect = _bad_request("message to edit not found")

        await stale_button(make_callback(uuid.uuid4().hex), bot)

    async def test_still_answers_when_the_edit_fails(self, bot):
        bot.edit_message_text.side_effect = _bad_request("message to edit not found")
        callback = make_callback(uuid.uuid4().hex)

        await stale_button(callback, bot)

        callback.answer.assert_awaited_once()

    async def test_tolerates_a_missing_message(self, bot):
        callback = make_callback(uuid.uuid4().hex)
        callback.message = None

        await stale_button(callback, bot)

        callback.answer.assert_awaited_once()
        bot.edit_message_text.assert_not_called()


class TestTheThreeTiersDoNotOverlap:
    def test_a_spacer_is_a_known_payload_so_order_matters(self):
        """CB_NOOP would be absorbed by the unroutable tier too — but silently.

        Both are silent, so the ordering between them is not user-visible; what
        matters is that neither lets a spacer reach the loud tier.
        """
        assert is_known_callback(CB_NOOP)

    def test_a_pre_migration_ptb_payload_reaches_the_loud_tier(self):
        assert not is_known_callback(uuid.uuid4().hex)

    def test_schema_drift_reaches_the_loud_tier(self):
        assert not is_known_callback("dset:" + uuid.uuid4().hex)
