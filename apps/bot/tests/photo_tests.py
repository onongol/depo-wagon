"""Tests for the photo step of the defect flow.

Telegram gives no end-of-album signal, so the step never waits for one: every
photo is recorded at once, an album is answered on its first photo only, and
the total is reported when the user presses Done.
"""

from unittest.mock import AsyncMock, MagicMock

from apps.bot.constants import BTN_DONE, UD_LAST_MEDIA_GROUP, UD_LAST_PHOTO_MSG
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.defect.photo.receive import (
    PhotoScene,
    clear_last_photo_keyboard,
)
from apps.bot.messages import BotMessages as M
from apps.bot.tests.builders import (
    CHAT_ID,
    MESSAGE_ID,
    make_bad_request,
    make_message,
)
from apps.bot.user_data import DefectData, PhotoEntry
from apps.defects.validators import MAX_PHOTO_BYTES


def _make_photo_message(
    file_id="AgACAgIAAx", size=1024, media_group_id=None, message_id=MESSAGE_ID
):
    message = make_message()
    message.message_id = message_id
    photo = MagicMock()
    photo.file_id = file_id
    photo.file_size = size
    message.photo = [photo]
    message.media_group_id = media_group_id

    sent = make_message()
    sent.message_id = 42
    message.answer = AsyncMock(return_value=sent)
    return message


def _make_bot():
    return MagicMock(edit_message_reply_markup=AsyncMock())


def _photos(*file_ids):
    return [PhotoEntry(file_id=f, message_id=i) for i, f in enumerate(file_ids)]


async def _file_ids(state):
    return [p.file_id for p in (await load_defect(state)).photos]


async def receive_photo(message, state, bot):
    await PhotoScene(wizard=AsyncMock()).receive(message, state, bot)


async def skip_photo(callback, state):
    await PhotoScene(wizard=AsyncMock()).skip(callback, state)


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
        bot.edit_message_reply_markup.side_effect = make_bad_request(
            "message not found"
        )
        await state.update_data({UD_LAST_PHOTO_MSG: [CHAT_ID, 42]})

        await clear_last_photo_keyboard(bot, state)

        assert UD_LAST_PHOTO_MSG not in await state.get_data()


class TestReceivePhoto:
    async def test_records_the_file_id_immediately(self, state):
        await save_defect(state, DefectData())

        await receive_photo(
            _make_photo_message(file_id="first", message_id=7), state, _make_bot()
        )

        assert (await load_defect(state)).photos == [
            PhotoEntry(file_id="first", message_id=7)
        ]

    async def test_records_a_serializable_message_reference(self, state):
        await save_defect(state, DefectData())

        await receive_photo(_make_photo_message(), state, _make_bot())

        assert (await state.get_data())[UD_LAST_PHOTO_MSG] == [CHAT_ID, 42]

    async def test_rejects_an_oversize_photo_without_recording_it(self, state):
        await save_defect(state, DefectData())
        message = _make_photo_message(size=MAX_PHOTO_BYTES + 1)

        await receive_photo(message, state, _make_bot())

        assert await _file_ids(state) == []
        assert UD_LAST_PHOTO_MSG not in await state.get_data()

    async def test_a_lone_photo_is_answered_with_the_running_count(self, state):
        await save_defect(state, DefectData(photos=_photos("a")))
        message = _make_photo_message()

        await receive_photo(message, state, _make_bot())

        text = message.answer.await_args.args[0]
        assert text == str(M.PHOTO_RECEIVED).format(count=2)

    async def test_the_answer_offers_done_rather_than_skip(self, state):
        await save_defect(state, DefectData())
        message = _make_photo_message()

        await receive_photo(message, state, _make_bot())

        markup = message.answer.await_args.kwargs["reply_markup"]
        assert markup.inline_keyboard[0][0].text == str(BTN_DONE)


class TestAlbum:
    async def test_every_photo_is_recorded_but_only_the_first_answered(self, state):
        await save_defect(state, DefectData())
        messages = [
            _make_photo_message(file_id=f"p{i}", media_group_id="mg-1", message_id=i)
            for i in range(3)
        ]

        for message in messages:
            await receive_photo(message, state, _make_bot())

        assert await _file_ids(state) == ["p0", "p1", "p2"]
        assert [m.answer.await_count for m in messages] == [1, 0, 0]
        assert messages[0].answer.await_args.args[0] == str(M.PHOTO_ALBUM_RECEIVING)

    async def test_photos_handled_out_of_order_are_kept_in_message_order(self, state):
        await save_defect(state, DefectData())

        for i in (2, 0, 1):
            message = _make_photo_message(
                file_id=f"p{i}", media_group_id="mg-1", message_id=i
            )
            await receive_photo(message, state, _make_bot())

        assert await _file_ids(state) == ["p0", "p1", "p2"]

    async def test_a_second_album_is_answered_again(self, state):
        await save_defect(state, DefectData())
        second = _make_photo_message(media_group_id="mg-2")

        await receive_photo(
            _make_photo_message(media_group_id="mg-1"), state, _make_bot()
        )
        await receive_photo(second, state, _make_bot())

        second.answer.assert_awaited_once()

    async def test_a_new_answer_strips_the_keyboard_from_the_last(self, state):
        await save_defect(state, DefectData())
        bot = _make_bot()

        await receive_photo(_make_photo_message(media_group_id="mg-1"), state, bot)
        await receive_photo(_make_photo_message(), state, bot)

        bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=CHAT_ID, message_id=42, reply_markup=None
        )


class TestSkipPhoto:
    async def test_reports_how_many_photos_were_attached(self, state, callback):
        await save_defect(state, DefectData(photos=_photos("a", "b", "c")))

        await skip_photo(callback, state)

        callback.answer.assert_awaited_once_with(str(M.PHOTOS_ATTACHED).format(count=3))

    async def test_skipping_without_photos_reports_nothing(self, state, callback):
        await save_defect(state, DefectData())

        await skip_photo(callback, state)

        callback.answer.assert_awaited_once_with(None)

    async def test_forgets_the_album_on_leaving_the_step(self, state, callback):
        await save_defect(state, DefectData(photos=_photos("a")))
        await state.update_data({UD_LAST_MEDIA_GROUP: "mg-1"})

        await skip_photo(callback, state)

        assert UD_LAST_MEDIA_GROUP not in await state.get_data()
