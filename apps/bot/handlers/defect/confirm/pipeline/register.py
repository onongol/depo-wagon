import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from apps.bot import services

if TYPE_CHECKING:
    from aiogram import Bot

    from apps.bot.user_data import DefectData
    from apps.core.models import Employee

logger = logging.getLogger(__name__)

_PHOTO_FETCH_TIMEOUT = 15.0


@dataclass
class PersistResult:
    """Outcome of persisting a defect: the saved record and downloaded photo bytes."""

    defect: object
    photo_bytes: list[bytes]


async def register_defect(
    defect_data: DefectData, employee: Employee, bot: Bot
) -> PersistResult:
    """Save defect and measurements, queue its photos for storage, fetch them for AI.
    Raises on the critical create_defect failure. Photo and measurement failures
    are non-critical: they are logged and skipped, never aborting the save.
    """
    saved_defect = await services.create_defect(defect_data, employee_id=employee.id)
    file_ids = [p.file_id for p in defect_data.photos]

    if file_ids:
        try:
            await services.queue_defect_photos(saved_defect.id, file_ids)
        except Exception as exc:
            logger.warning("Queueing photos failed: %s", exc, exc_info=True)

    async def _fetch_photo(idx: int, file_id: str) -> bytes | None:
        """Download a photo for the analysis; None if it failed or was too slow."""
        try:
            return await asyncio.wait_for(
                services.download_photo(bot, file_id), timeout=_PHOTO_FETCH_TIMEOUT
            )
        except TimeoutError:
            logger.warning(
                "Photo download for analysis timed out after %.0fs (idx=%d)",
                _PHOTO_FETCH_TIMEOUT,
                idx,
            )
            return None
        except Exception as exc:
            logger.warning(
                "Photo download failed (idx=%d): %s", idx, exc, exc_info=True
            )
            return None

    photo_results = await asyncio.gather(
        *[_fetch_photo(i, file_id) for i, file_id in enumerate(file_ids)]
    )
    all_photo_bytes: list[bytes] = [b for b in photo_results if b is not None]

    # Save measurements if any. Failure is non-critical, just log it.
    if defect_data.measurements:
        try:
            await services.create_measurements_bulk(
                saved_defect.id, defect_data.measurements
            )
        except Exception as exc:
            logger.warning("Measurements save failed: %s", exc, exc_info=True)

    return PersistResult(defect=saved_defect, photo_bytes=all_photo_bytes)
