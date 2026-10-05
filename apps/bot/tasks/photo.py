import asyncio
import logging

from aiogram.exceptions import TelegramBadRequest
from celery import shared_task

logger = logging.getLogger(__name__)


async def _download(file_id: str) -> bytes | None:
    from apps.bot.bot import make_bot
    from apps.bot.services.photo import download_photo

    async with make_bot() as bot:
        return await download_photo(bot, file_id)


@shared_task(
    bind=True,
    max_retries=5,
    name="bot.save_defect_photos",
)
def save_defect_photos_task(self, defect_id: str, file_ids: list[str]) -> None:
    """Store a defect's photos one by one, resuming after the last saved on retry."""
    from django.core.files.base import ContentFile

    from apps.defects.models import DefectPhoto

    for idx, file_id in enumerate(file_ids):
        filename = f"bot_{defect_id}_{idx + 1}_{file_id[-8:]}.jpg"
        saved = DefectPhoto.objects.filter(
            defect_id=defect_id, image__endswith=filename
        )
        if saved.exists():
            continue

        try:
            file_bytes = asyncio.run(_download(file_id))
            if file_bytes is None:
                continue
            photo = DefectPhoto(defect_id=defect_id)
            photo.image.save(filename, ContentFile(file_bytes), save=True)
        except TelegramBadRequest:
            logger.warning(
                "Telegram refused photo %d of defect %s",
                idx + 1,
                defect_id,
                exc_info=True,
            )
        except Exception as exc:
            logger.exception("Saving photo %d of defect %s failed", idx + 1, defect_id)
            raise self.retry(exc=exc, countdown=60 * 2**self.request.retries) from exc
