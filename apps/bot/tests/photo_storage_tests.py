"""Defect photos leave the bot as file ids; the worker downloads and stores them."""

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import GetFile
from django.core.files.base import ContentFile
from model_bakery import baker

from apps.bot.services.photo import download_photo, queue_defect_photos
from apps.bot.tasks import save_defect_photos_task
from apps.defects.models import DefectPhoto
from apps.defects.validators import MAX_PHOTO_BYTES


def _make_bot(size=1000, content=b"img"):
    file = MagicMock(file_size=size, file_path="photos/x.jpg")
    return MagicMock(
        get_file=AsyncMock(return_value=file),
        download_file=AsyncMock(return_value=io.BytesIO(content)),
    )


def _downloads(**by_file_id):
    """Stand in for the worker's Telegram download; an exception value is raised."""

    async def download(file_id):
        result = by_file_id[file_id]
        if isinstance(result, Exception):
            raise result
        return result

    return patch("apps.bot.tasks._download", AsyncMock(side_effect=download))


def _stored_names(defect):
    photos = DefectPhoto.objects.filter(defect=defect).order_by("uploaded_at", "pk")
    return [photo.image.name.rsplit("/", 1)[-1] for photo in photos]


@pytest.fixture
def defect(db):
    return baker.make("defects.Defect", wagon__manufacture_year=2020)


class TestDownloadPhoto:
    async def test_returns_the_file_bytes(self):
        assert await download_photo(_make_bot(content=b"jpeg"), "file") == b"jpeg"

    async def test_an_oversize_photo_is_not_downloaded(self):
        bot = _make_bot(size=MAX_PHOTO_BYTES + 1)

        assert await download_photo(bot, "file") is None
        bot.download_file.assert_not_called()


class TestQueueDefectPhotos:
    async def test_queues_a_json_safe_id_and_the_file_ids(self):
        defect_id = uuid.uuid4()

        with patch("apps.bot.tasks.save_defect_photos_task.delay") as delay:
            await queue_defect_photos(defect_id, ["a", "b"])

        delay.assert_called_once_with(str(defect_id), ["a", "b"])


class TestSaveDefectPhotosTask:
    def test_stores_every_photo_in_the_order_given(self, defect):
        with _downloads(first=b"1", second=b"2"):
            save_defect_photos_task(str(defect.id), ["first", "second"])

        assert _stored_names(defect) == [
            f"bot_{defect.id}_1_first.jpg",
            f"bot_{defect.id}_2_second.jpg",
        ]

    def test_a_retry_skips_photos_already_stored(self, defect):
        DefectPhoto(defect=defect).image.save(
            f"bot_{defect.id}_1_first.jpg", ContentFile(b"1"), save=True
        )

        with _downloads(second=b"2") as download:
            save_defect_photos_task(str(defect.id), ["first", "second"])

        download.assert_awaited_once_with("second")
        assert len(_stored_names(defect)) == 2

    def test_an_oversize_photo_is_skipped(self, defect):
        with _downloads(big=None, small=b"2"):
            save_defect_photos_task(str(defect.id), ["big", "small"])

        assert _stored_names(defect) == [f"bot_{defect.id}_2_small.jpg"]

    def test_a_photo_telegram_refuses_is_skipped_not_retried(self, defect):
        refused = TelegramBadRequest(
            method=GetFile(file_id="gone"), message="file not found"
        )

        with (
            _downloads(gone=refused, kept=b"2"),
            patch.object(save_defect_photos_task, "retry") as retry,
        ):
            save_defect_photos_task(str(defect.id), ["gone", "kept"])

        retry.assert_not_called()
        assert _stored_names(defect) == [f"bot_{defect.id}_2_kept.jpg"]

    def test_a_transient_failure_retries_before_later_photos_are_stored(self, defect):
        with (
            _downloads(first=ConnectionError("telegram is down"), second=b"2"),
            patch.object(
                save_defect_photos_task, "retry", return_value=RuntimeError("retrying")
            ) as retry,
            pytest.raises(RuntimeError, match="retrying"),
        ):
            save_defect_photos_task(str(defect.id), ["first", "second"])

        retry.assert_called_once()
        assert _stored_names(defect) == []
