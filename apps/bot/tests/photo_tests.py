"""Tests for the photo step of the defect flow.

The album debounce and the last-keyboard bookkeeping had no coverage. These
lock in the current PTB behaviour before the aiogram rewrite replaces the
JobQueue with an asyncio debounce.
"""

import json
from unittest.mock import AsyncMock, MagicMock

from telegram.error import TelegramError

from apps.bot.constants import UD_DEFECT, UD_LAST_PHOTO_MSG
from apps.bot.handlers.defect.photo.jobs import (
    clear_last_photo_keyboard,
    flush_media_group,
)
from apps.bot.handlers.defect.photo.receive import receive_photo
from apps.bot.states import PHOTO
from apps.bot.user_data import DefectData
from apps.defects.validators import MAX_PHOTO_BYTES


def _make_sent_message(chat_id=555, message_id=42):
    msg = MagicMock()
    msg.chat_id = chat_id
    msg.message_id = message_id
    return msg


def _make_photo_update(file_id="AgACAgIAAx", size=1024, media_group_id=None):
    update = MagicMock()
    photo = MagicMock()
    photo.file_id = file_id
    photo.file_size = size
    update.message.photo = [photo]
    update.message.media_group_id = media_group_id
    update.message.reply_text = AsyncMock(return_value=_make_sent_message())
    update.effective_user.id = 12345
    update.effective_chat.id = 555
    return update


class TestClearLastPhotoKeyboard:
    async def test_does_nothing_when_no_message_was_recorded(self):
        bot = MagicMock()
        bot.edit_message_reply_markup = AsyncMock()

        await clear_last_photo_keyboard(bot, {})

        bot.edit_message_reply_markup.assert_not_called()

    async def test_strips_the_keyboard_by_chat_and_message_id(self):
        bot = MagicMock()
        bot.edit_message_reply_markup = AsyncMock()
        user_data = {UD_LAST_PHOTO_MSG: [555, 42]}

        await clear_last_photo_keyboard(bot, user_data)

        bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=555, message_id=42, reply_markup=None
        )
        assert UD_LAST_PHOTO_MSG not in user_data

    async def test_swallows_telegram_errors_on_deleted_messages(self):
        bot = MagicMock()
        bot.edit_message_reply_markup = AsyncMock(side_effect=TelegramError("gone"))

        await clear_last_photo_keyboard(bot, {UD_LAST_PHOTO_MSG: [555, 42]})

    async def test_pops_the_reference_even_when_the_edit_fails(self):
        bot = MagicMock()
        bot.edit_message_reply_markup = AsyncMock(side_effect=TelegramError("gone"))
        user_data = {UD_LAST_PHOTO_MSG: [555, 42]}

        await clear_last_photo_keyboard(bot, user_data)

        assert UD_LAST_PHOTO_MSG not in user_data


class TestReceivePhoto:
    async def test_records_a_serializable_message_reference(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        mock_context.bot.edit_message_reply_markup = AsyncMock()
        update = _make_photo_update()

        result = await receive_photo(update, mock_context)

        assert mock_context.user_data[UD_LAST_PHOTO_MSG] == [555, 42]
        assert json.dumps(mock_context.user_data[UD_LAST_PHOTO_MSG])
        assert result == PHOTO

    async def test_appends_the_largest_photo_file_id(self, mock_context):
        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        mock_context.bot.edit_message_reply_markup = AsyncMock()

        await receive_photo(_make_photo_update(file_id="first"), mock_context)

        assert defect.photo_file_ids == ["first"]

    async def test_rejects_an_oversize_photo_without_recording_it(self, mock_context):
        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        update = _make_photo_update(size=MAX_PHOTO_BYTES + 1)

        result = await receive_photo(update, mock_context)

        assert defect.photo_file_ids == []
        assert UD_LAST_PHOTO_MSG not in mock_context.user_data
        assert result == PHOTO

    async def test_album_photo_defers_the_reply_to_a_job(self, mock_context):
        defect = DefectData()
        mock_context.user_data[UD_DEFECT] = defect
        mock_context.job_queue.get_jobs_by_name.return_value = []
        update = _make_photo_update(media_group_id="mg-1")

        await receive_photo(update, mock_context)

        assert defect.photo_file_ids == ["AgACAgIAAx"]
        update.message.reply_text.assert_not_called()
        mock_context.job_queue.run_once.assert_called_once()
        assert mock_context.job_queue.run_once.call_args.kwargs["when"] == 0.5

    async def test_album_photo_cancels_the_previous_pending_job(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        pending = MagicMock()
        mock_context.job_queue.get_jobs_by_name.return_value = [pending]

        await receive_photo(_make_photo_update(media_group_id="mg-1"), mock_context)

        pending.schedule_removal.assert_called_once()

    async def test_album_job_is_named_per_user(self, mock_context):
        mock_context.user_data[UD_DEFECT] = DefectData()
        mock_context.job_queue.get_jobs_by_name.return_value = []

        await receive_photo(_make_photo_update(media_group_id="mg-1"), mock_context)

        kwargs = mock_context.job_queue.run_once.call_args.kwargs
        assert str(12345) in kwargs["name"]
        assert kwargs["user_id"] == 12345
        assert kwargs["chat_id"] == 555


class TestFlushMediaGroup:
    def _context(self, user_data):
        context = MagicMock()
        context.job.user_id = 12345
        context.job.chat_id = 555
        context.application.user_data = {12345: user_data}
        context.bot.send_message = AsyncMock(return_value=_make_sent_message(555, 99))
        context.bot.edit_message_reply_markup = AsyncMock()
        return context

    async def test_reports_the_collected_photo_count_once(self):
        user_data = {UD_DEFECT: DefectData(photo_file_ids=["a", "b", "c"])}
        context = self._context(user_data)

        await flush_media_group(context)

        context.bot.send_message.assert_awaited_once()
        assert "3" in context.bot.send_message.call_args.kwargs["text"]

    async def test_records_the_new_message_reference(self):
        user_data = {UD_DEFECT: DefectData(photo_file_ids=["a"])}
        context = self._context(user_data)

        await flush_media_group(context)

        assert user_data[UD_LAST_PHOTO_MSG] == [555, 99]
        assert json.dumps(user_data[UD_LAST_PHOTO_MSG])

    async def test_strips_the_keyboard_from_the_previous_count_message(self):
        user_data = {
            UD_DEFECT: DefectData(photo_file_ids=["a"]),
            UD_LAST_PHOTO_MSG: [555, 42],
        }
        context = self._context(user_data)

        await flush_media_group(context)

        context.bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=555, message_id=42, reply_markup=None
        )

    async def test_reports_zero_when_the_flow_was_cancelled_mid_album(self):
        context = self._context({})

        await flush_media_group(context)

        assert "0" in context.bot.send_message.call_args.kwargs["text"]
