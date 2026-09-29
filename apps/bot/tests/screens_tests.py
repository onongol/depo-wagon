from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    Chat,
    InaccessibleMessage,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from apps.bot.constants import UD_SCREEN
from apps.bot.tests.builders import (
    SENT_ID,
    make_bad_request,
    make_bot,
    make_callback,
    make_message,
)
from apps.bot.utils.screens import (
    answer_anew,
    delete_input,
    edit_or_send,
    show_screen,
)


def _callback_on(message) -> MagicMock:
    callback = make_callback(user_id=777)
    callback.message = message
    callback.bot = MagicMock(edit_message_text=AsyncMock(), send_message=AsyncMock())
    return callback


def _inaccessible() -> InaccessibleMessage:
    return InaccessibleMessage(chat=Chat(id=777, type="private"), message_id=5, date=0)


class TestEditOrSend:
    """The screen reaches the user whatever became of the button's message."""

    async def test_edits_the_message_in_place_by_id(self):
        callback = _callback_on(make_message())

        await edit_or_send(callback, text="x")

        callback.bot.edit_message_text.assert_awaited_once_with(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=None,
            text="x",
        )
        callback.message.answer.assert_not_awaited()

    async def test_an_inaccessible_message_is_edited_too(self):
        """It has no edit methods of its own, but its ids are enough."""
        callback = _callback_on(_inaccessible())

        await edit_or_send(callback, text="x")

        callback.bot.edit_message_text.assert_awaited_once_with(
            chat_id=777, message_id=5, reply_markup=None, text="x"
        )

    async def test_an_unchanged_screen_is_left_alone(self):
        callback = _callback_on(make_message())
        callback.bot.edit_message_text.side_effect = make_bad_request(
            "Bad Request: message is not modified"
        )

        await edit_or_send(callback, text="x")

        callback.message.answer.assert_not_awaited()

    @pytest.mark.parametrize(
        "refusal", ["message can't be edited", "message to edit not found"]
    )
    async def test_a_refused_edit_is_sent_anew(self, refusal):
        callback = _callback_on(make_message())
        callback.bot.edit_message_text.side_effect = make_bad_request(
            f"Bad Request: {refusal}"
        )

        await edit_or_send(callback, text="x")

        callback.message.answer.assert_awaited_once_with(reply_markup=None, text="x")

    async def test_a_screen_telegram_rejects_is_raised_not_resent(self):
        """Resending bad content fails the same way and hides the real cause."""
        callback = _callback_on(make_message())
        callback.bot.edit_message_text.side_effect = make_bad_request(
            "Bad Request: message is too long"
        )

        with pytest.raises(TelegramBadRequest, match="too long"):
            await edit_or_send(callback, text="x")

        callback.message.answer.assert_not_awaited()

    async def test_the_inline_keyboard_rides_the_edit_and_the_resend(self):
        markup = InlineKeyboardMarkup(inline_keyboard=[])
        callback = _callback_on(make_message())
        callback.bot.edit_message_text.side_effect = make_bad_request(
            "Bad Request: message can't be edited"
        )

        await edit_or_send(callback, text="x", reply_markup=markup)

        assert (
            callback.bot.edit_message_text.await_args.kwargs["reply_markup"] is markup
        )
        callback.message.answer.assert_awaited_once_with(reply_markup=markup, text="x")

    async def test_without_a_message_it_writes_to_the_user(self):
        callback = _callback_on(None)

        await edit_or_send(callback, text="x")

        callback.bot.send_message.assert_awaited_once_with(
            777, reply_markup=None, text="x"
        )


class TestAnswerAnew:
    """A reply keyboard only rides a new message; the tapped one loses its buttons."""

    MENU = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Menu")]])

    def _callback(self, message) -> MagicMock:
        callback = _callback_on(message)
        callback.bot.edit_message_reply_markup = AsyncMock()
        return callback

    async def test_strips_the_buttons_and_answers_below(self):
        callback = self._callback(make_message())

        await answer_anew(callback, text="x", reply_markup=self.MENU)

        callback.bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=None,
        )
        callback.message.answer.assert_awaited_once_with(
            reply_markup=self.MENU, text="x"
        )

    @pytest.mark.parametrize(
        "refusal", ["message is not modified", "message to edit not found"]
    )
    async def test_a_refused_strip_still_answers(self, refusal):
        callback = self._callback(make_message())
        callback.bot.edit_message_reply_markup.side_effect = make_bad_request(
            f"Bad Request: {refusal}"
        )

        await answer_anew(callback, text="x", reply_markup=self.MENU)

        callback.message.answer.assert_awaited_once()

    async def test_an_inaccessible_message_is_stripped_by_its_ids(self):
        callback = self._callback(_inaccessible())

        with patch.object(InaccessibleMessage, "answer", AsyncMock()) as answer:
            await answer_anew(callback, text="x", reply_markup=self.MENU)

        callback.bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=777, message_id=5, reply_markup=None
        )
        answer.assert_awaited_once_with(reply_markup=self.MENU, text="x")

    async def test_without_a_message_it_writes_to_the_user(self):
        callback = self._callback(None)

        await answer_anew(callback, text="x", reply_markup=self.MENU)

        callback.bot.edit_message_reply_markup.assert_not_awaited()
        callback.bot.send_message.assert_awaited_once_with(
            777, reply_markup=self.MENU, text="x"
        )


class TestDeleteInput:
    async def test_the_message_is_deleted(self):
        message = make_message("80035668")

        await delete_input(message)

        message.delete.assert_awaited_once()

    async def test_one_already_gone_is_no_error(self):
        message = make_message("80035668")
        message.delete.side_effect = make_bad_request(
            "Bad Request: message to delete not found"
        )

        await delete_input(message)


class TestShowScreen:
    """One message per form: edited by its stored ids, sent only when it must be."""

    CHAT = 12345
    SCREEN = [CHAT, 7]

    async def _stored(self, state):
        await state.update_data({UD_SCREEN: self.SCREEN})

    async def test_the_stored_screen_is_edited_in_place(self, state):
        await self._stored(state)
        bot = make_bot()

        await show_screen(bot, state, self.CHAT, text="x", reply_markup=None)

        bot.edit_message_text.assert_awaited_once_with(
            chat_id=self.CHAT, message_id=7, text="x", reply_markup=None
        )
        bot.send_message.assert_not_awaited()

    async def test_an_unchanged_screen_is_left_alone(self, state):
        await self._stored(state)
        bot = make_bot()
        bot.edit_message_text.side_effect = make_bad_request(
            "Bad Request: message is not modified"
        )

        await show_screen(bot, state, self.CHAT, text="x")

        bot.send_message.assert_not_awaited()
        assert (await state.get_data())[UD_SCREEN] == self.SCREEN

    @pytest.mark.parametrize(
        "refusal", ["message can't be edited", "message to edit not found"]
    )
    async def test_a_screen_gone_or_too_old_is_sent_anew(self, state, refusal):
        await self._stored(state)
        bot = make_bot()
        bot.edit_message_text.side_effect = make_bad_request(f"Bad Request: {refusal}")

        await show_screen(bot, state, self.CHAT, text="x")

        bot.send_message.assert_awaited_once_with(self.CHAT, text="x")
        assert (await state.get_data())[UD_SCREEN] == [self.CHAT, SENT_ID]

    async def test_a_screen_telegram_rejects_is_raised_not_resent(self, state):
        await self._stored(state)
        bot = make_bot()
        bot.edit_message_text.side_effect = make_bad_request(
            "Bad Request: message is too long"
        )

        with pytest.raises(TelegramBadRequest, match="too long"):
            await show_screen(bot, state, self.CHAT, text="x")

        bot.send_message.assert_not_awaited()

    async def test_without_one_it_is_sent_and_stored(self, state):
        bot = make_bot()

        await show_screen(bot, state, self.CHAT, text="x")

        bot.send_message.assert_awaited_once_with(self.CHAT, text="x")
        assert (await state.get_data())[UD_SCREEN] == [self.CHAT, SENT_ID]

    async def test_without_one_a_tap_adopts_its_message(self, state):
        """A form begun before the screen was stored."""
        bot = make_bot()
        tapped = make_message()

        await show_screen(bot, state, self.CHAT, tapped=tapped, text="x")

        bot.edit_message_text.assert_awaited_once_with(
            chat_id=tapped.chat.id, message_id=tapped.message_id, text="x"
        )
        stored = (await state.get_data())[UD_SCREEN]
        assert stored == [tapped.chat.id, tapped.message_id]

    async def test_a_stored_screen_wins_over_the_tapped_message(self, state):
        await self._stored(state)
        bot = make_bot()

        await show_screen(bot, state, self.CHAT, tapped=make_message(), text="x")

        assert bot.edit_message_text.await_args.kwargs["message_id"] == 7

    async def test_below_sends_it_anew_and_takes_the_old_one_down(self, state):
        await self._stored(state)
        bot = make_bot()

        await show_screen(bot, state, self.CHAT, below=True, text="x")

        bot.edit_message_text.assert_not_awaited()
        bot.send_message.assert_awaited_once_with(self.CHAT, text="x")
        bot.delete_message.assert_awaited_once_with(chat_id=self.CHAT, message_id=7)
        assert (await state.get_data())[UD_SCREEN] == [self.CHAT, SENT_ID]

    async def test_an_old_screen_that_cannot_go_loses_its_buttons(self, state):
        await self._stored(state)
        bot = make_bot()
        bot.delete_message.side_effect = make_bad_request(
            "Bad Request: message can't be deleted"
        )

        await show_screen(bot, state, self.CHAT, below=True, text="x")

        bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=self.CHAT, message_id=7, reply_markup=None
        )
