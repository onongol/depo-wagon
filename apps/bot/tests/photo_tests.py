"""Tests for the photo step of the defect flow.

Telegram gives no end-of-album signal, so the step never waits for one: every
photo is recorded at once, an album is answered on its first photo only, and
the total is reported when the user presses Done.
"""

from unittest.mock import AsyncMock, MagicMock

from apps.bot.constants import BTN_DONE, UD_LAST_MEDIA_GROUP, UD_SCREEN
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.defect.photo.receive import PhotoScene
from apps.bot.handlers.defect.text import (
    build_album_receiving_text,
    build_photo_received_text,
    build_photo_too_large_text,
    build_photos_attached_toast,
)
from apps.bot.tests.builders import CHAT_ID, MESSAGE_ID, SENT_ID, make_message
from apps.bot.user_data import DefectData, PhotoEntry
from apps.defects.validators import MAX_PHOTO_BYTES

OLD_SCREEN = [CHAT_ID, 500]


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
    return message


def _photos(*file_ids):
    return [PhotoEntry(file_id=f, message_id=i) for i, f in enumerate(file_ids)]


async def _file_ids(state):
    return [p.file_id for p in (await load_defect(state)).photos]


def _screen_text(message) -> str:
    return message.bot.send_message.await_args.kwargs["text"]


async def receive_photo(message, state):
    await PhotoScene(wizard=AsyncMock()).receive(message, state)


async def skip_photo(callback, state):
    await PhotoScene(wizard=AsyncMock()).skip(callback, state)


class TestReceivePhoto:
    async def test_records_the_file_id_immediately(self, state):
        await save_defect(state, DefectData())

        await receive_photo(_make_photo_message(file_id="first", message_id=7), state)

        assert (await load_defect(state)).photos == [
            PhotoEntry(file_id="first", message_id=7)
        ]

    async def test_the_photo_stays_and_the_screen_goes_under_it(self, state):
        await save_defect(state, DefectData())
        await state.update_data({UD_SCREEN: OLD_SCREEN})
        message = _make_photo_message()

        await receive_photo(message, state)

        message.delete.assert_not_awaited()
        message.bot.send_message.assert_awaited_once()
        message.bot.delete_message.assert_awaited_once_with(
            chat_id=CHAT_ID, message_id=OLD_SCREEN[1]
        )
        assert (await state.get_data())[UD_SCREEN] == [CHAT_ID, SENT_ID]

    async def test_rejects_an_oversize_photo_without_recording_it(self, state):
        await save_defect(state, DefectData())
        message = _make_photo_message(size=MAX_PHOTO_BYTES + 1)

        await receive_photo(message, state)

        assert await _file_ids(state) == []
        too_large = build_photo_too_large_text().render()[0]
        assert _screen_text(message).startswith(too_large)

    async def test_a_lone_photo_gets_the_running_count(self, state):
        await save_defect(state, DefectData(photos=_photos("a")))
        message = _make_photo_message()

        await receive_photo(message, state)

        assert _screen_text(message) == build_photo_received_text(2).render()[0]

    async def test_the_screen_offers_done_rather_than_skip(self, state):
        await save_defect(state, DefectData())
        message = _make_photo_message()

        await receive_photo(message, state)

        markup = message.bot.send_message.await_args.kwargs["reply_markup"]
        assert markup.inline_keyboard[0][0].text == str(BTN_DONE)


class TestAlbum:
    async def test_every_photo_is_recorded_but_only_the_first_answered(self, state):
        await save_defect(state, DefectData())
        messages = [
            _make_photo_message(file_id=f"p{i}", media_group_id="mg-1", message_id=i)
            for i in range(3)
        ]

        for message in messages:
            await receive_photo(message, state)

        assert await _file_ids(state) == ["p0", "p1", "p2"]
        assert [m.bot.send_message.await_count for m in messages] == [1, 0, 0]
        receiving = build_album_receiving_text().render()[0]
        assert _screen_text(messages[0]).startswith(receiving)

    async def test_photos_handled_out_of_order_are_kept_in_message_order(self, state):
        await save_defect(state, DefectData())

        for i in (2, 0, 1):
            message = _make_photo_message(
                file_id=f"p{i}", media_group_id="mg-1", message_id=i
            )
            await receive_photo(message, state)

        assert await _file_ids(state) == ["p0", "p1", "p2"]

    async def test_a_second_album_is_answered_again(self, state):
        await save_defect(state, DefectData())
        second = _make_photo_message(media_group_id="mg-2")

        await receive_photo(_make_photo_message(media_group_id="mg-1"), state)
        await receive_photo(second, state)

        second.bot.send_message.assert_awaited_once()


class TestSkipPhoto:
    async def test_reports_how_many_photos_were_attached(self, state, callback):
        await save_defect(state, DefectData(photos=_photos("a", "b", "c")))

        await skip_photo(callback, state)

        callback.answer.assert_awaited_once_with(build_photos_attached_toast(3))

    async def test_skipping_without_photos_reports_nothing(self, state, callback):
        await save_defect(state, DefectData())

        await skip_photo(callback, state)

        callback.answer.assert_awaited_once_with(None)

    async def test_forgets_the_album_on_leaving_the_step(self, state, callback):
        await save_defect(state, DefectData(photos=_photos("a")))
        await state.update_data({UD_LAST_MEDIA_GROUP: "mg-1"})

        await skip_photo(callback, state)

        assert UD_LAST_MEDIA_GROUP not in await state.get_data()
