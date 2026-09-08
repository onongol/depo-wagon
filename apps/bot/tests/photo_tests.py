"""Tests for the photo step of the defect flow.

The album debounce is the part with no PTB analogue left: JobQueue is gone and
a plain asyncio task takes its place. These pin the properties that matter —
each photo is recorded immediately, and exactly one acknowledgement follows.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText

from apps.bot.constants import UD_LAST_PHOTO_MSG
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.defect.photo.jobs import (
    FLUSH_DELAY,
    cancel_pending_flushes,
    clear_last_photo_keyboard,
    flush_media_group,
    schedule_flush,
)
from apps.bot.handlers.defect.photo.receive import receive_photo
from apps.bot.tests.builders import CHAT_ID, USER_ID, make_message
from apps.bot.user_data import DefectData
from apps.defects.validators import MAX_PHOTO_BYTES


@pytest.fixture(autouse=True)
async def _no_pending_flushes():
    yield
    await cancel_pending_flushes()


def _make_photo_message(file_id="AgACAgIAAx", size=1024, media_group_id=None):
    message = make_message()
    photo = MagicMock()
    photo.file_id = file_id
    photo.file_size = size
    message.photo = [photo]
    message.media_group_id = media_group_id

    sent = make_message()
    sent.message_id = 42
    message.answer = AsyncMock(return_value=sent)
    return message


def _make_bot(sent_message_id=99):
    sent = make_message()
    sent.message_id = sent_message_id
    return MagicMock(
        send_message=AsyncMock(return_value=sent),
        edit_message_reply_markup=AsyncMock(),
    )


def _bad_request(text: str) -> TelegramBadRequest:
    return TelegramBadRequest(
        method=EditMessageText(chat_id=1, message_id=1, text="x"), message=text
    )


class TestClearLastPhotoKeyboard:
    async def test_does_nothing_when_no_message_was_recorded(self, state):
        bot = _make_bot()

        await clear_last_photo_keyboard(bot, state)

        bot.edit_message_reply_markup.assert_not_called()

    async def test_strips_the_keyboard_by_chat_and_message_id(self, state):
        bot = _make_bot()
        await state.update_data({UD_LAST_PHOTO_MSG: [CHAT_ID, 42]})

        await clear_last_photo_keyboard(bot, state)

        bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=CHAT_ID, message_id=42, reply_markup=None
        )
        assert UD_LAST_PHOTO_MSG not in await state.get_data()

    async def test_swallows_telegram_errors_on_deleted_messages(self, state):
        bot = _make_bot()
        bot.edit_message_reply_markup.side_effect = _bad_request("message not found")
        await state.update_data({UD_LAST_PHOTO_MSG: [CHAT_ID, 42]})

        await clear_last_photo_keyboard(bot, state)

        assert UD_LAST_PHOTO_MSG not in await state.get_data()


class TestReceivePhoto:
    async def test_records_the_file_id_immediately(self, state):
        await save_defect(state, DefectData())

        await receive_photo(_make_photo_message(file_id="first"), state, _make_bot())

        assert (await load_defect(state)).photo_file_ids == ["first"]

    async def test_records_a_serializable_message_reference(self, state):
        await save_defect(state, DefectData())

        await receive_photo(_make_photo_message(), state, _make_bot())

        assert (await state.get_data())[UD_LAST_PHOTO_MSG] == [CHAT_ID, 42]

    async def test_rejects_an_oversize_photo_without_recording_it(self, state):
        await save_defect(state, DefectData())
        message = _make_photo_message(size=MAX_PHOTO_BYTES + 1)

        await receive_photo(message, state, _make_bot())

        assert (await load_defect(state)).photo_file_ids == []
        assert UD_LAST_PHOTO_MSG not in await state.get_data()

    async def test_an_album_photo_is_recorded_but_not_acknowledged_yet(self, state):
        await save_defect(state, DefectData())
        message = _make_photo_message(media_group_id="mg-1")

        await receive_photo(message, state, _make_bot())

        assert (await load_defect(state)).photo_file_ids == ["AgACAgIAAx"]
        message.answer.assert_not_called()

    async def test_a_whole_album_yields_one_acknowledgement(self, state):
        await save_defect(state, DefectData())
        bot = _make_bot()

        for i in range(3):
            await receive_photo(
                _make_photo_message(file_id=f"p{i}", media_group_id="mg-1"), state, bot
            )
        await asyncio.sleep(FLUSH_DELAY * 3)

        assert (await load_defect(state)).photo_file_ids == ["p0", "p1", "p2"]
        bot.send_message.assert_awaited_once()
        assert "3" in bot.send_message.await_args.kwargs["text"]

    async def test_a_single_photo_is_acknowledged_at_once(self, state):
        await save_defect(state, DefectData())
        message = _make_photo_message()

        await receive_photo(message, state, _make_bot())

        message.answer.assert_awaited_once()


class TestScheduleFlush:
    async def test_the_last_photo_wins(self, state):
        """Each arrival cancels the pending acknowledgement and reschedules."""
        await save_defect(state, DefectData(photo_file_ids=["a", "b"]))
        bot = _make_bot()

        for _ in range(4):
            schedule_flush(bot, state, chat_id=CHAT_ID, user_id=USER_ID)
        await asyncio.sleep(FLUSH_DELAY * 3)

        bot.send_message.assert_awaited_once()

    async def test_different_users_do_not_cancel_each_other(self, state):
        await save_defect(state, DefectData(photo_file_ids=["a"]))
        bot = _make_bot()

        schedule_flush(bot, state, chat_id=CHAT_ID, user_id=1)
        schedule_flush(bot, state, chat_id=CHAT_ID, user_id=2)
        await asyncio.sleep(FLUSH_DELAY * 3)

        assert bot.send_message.await_count == 2

    async def test_shutdown_cancels_a_pending_acknowledgement(self, state):
        await save_defect(state, DefectData(photo_file_ids=["a"]))
        bot = _make_bot()

        schedule_flush(bot, state, chat_id=CHAT_ID, user_id=USER_ID)
        await cancel_pending_flushes()
        await asyncio.sleep(FLUSH_DELAY * 2)

        bot.send_message.assert_not_called()


class TestFlushMediaGroup:
    async def test_reports_the_collected_photo_count(self, state):
        await save_defect(state, DefectData(photo_file_ids=["a", "b", "c"]))
        bot = _make_bot()

        await flush_media_group(bot, state, chat_id=CHAT_ID, user_id=USER_ID)

        bot.send_message.assert_awaited_once()
        assert "3" in bot.send_message.await_args.kwargs["text"]

    async def test_records_the_new_message_reference(self, state):
        await save_defect(state, DefectData(photo_file_ids=["a"]))
        bot = _make_bot(sent_message_id=99)

        await flush_media_group(bot, state, chat_id=CHAT_ID, user_id=USER_ID)

        assert (await state.get_data())[UD_LAST_PHOTO_MSG] == [CHAT_ID, 99]

    async def test_strips_the_keyboard_from_the_previous_count_message(self, state):
        await save_defect(state, DefectData(photo_file_ids=["a"]))
        await state.update_data({UD_LAST_PHOTO_MSG: [CHAT_ID, 42]})
        bot = _make_bot()

        await flush_media_group(bot, state, chat_id=CHAT_ID, user_id=USER_ID)

        bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=CHAT_ID, message_id=42, reply_markup=None
        )

    async def test_reports_zero_when_the_flow_was_cancelled_mid_album(self, state):
        bot = _make_bot()

        await flush_media_group(bot, state, chat_id=CHAT_ID, user_id=USER_ID)

        assert "0" in bot.send_message.await_args.kwargs["text"]
