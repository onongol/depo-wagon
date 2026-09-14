import logging
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async

from apps.defects.validators import MAX_PHOTO_BYTES

if TYPE_CHECKING:
    from aiogram import Bot

logger = logging.getLogger(__name__)


async def download_photo(bot: Bot, file_id: str) -> bytes | None:
    """Photo bytes from Telegram, or None when it exceeds the size cap."""
    file = await bot.get_file(file_id)
    if file.file_size and file.file_size > MAX_PHOTO_BYTES:
        logger.warning("Photo too large (%d bytes), skipping", file.file_size)
        return None
    buffer = await bot.download_file(file.file_path)
    return buffer.read()


@sync_to_async
def queue_defect_photos(defect_id, file_ids: list[str]) -> None:
    """Hand the photos to the worker, which stores them in order."""
    from apps.bot.tasks import save_defect_photos_task

    save_defect_photos_task.delay(str(defect_id), file_ids)
