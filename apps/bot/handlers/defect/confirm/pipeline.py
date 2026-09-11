import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from apps.ai_service.analysis import analyze_defect
from apps.bot import services
from apps.defects.validators import MAX_PHOTO_BYTES

if TYPE_CHECKING:
    import uuid

    from aiogram import Bot

    from apps.bot.user_data import DefectData
    from apps.core.models import Employee

logger = logging.getLogger(__name__)

_ANALYSIS_TIMEOUT = 60.0


@dataclass
class PersistResult:
    """Outcome of persisting a defect: the saved record and downloaded photo bytes."""

    defect: object
    photo_bytes: list[bytes]


async def _download_photo(bot: Bot, file_id: str) -> bytes | None:
    """Photo bytes from Telegram, or None when it exceeds the size cap.

    PTB's File.download_as_bytearray has no aiogram counterpart; download_file
    returns a BytesIO instead.
    """
    file = await bot.get_file(file_id)
    if file.file_size and file.file_size > MAX_PHOTO_BYTES:
        logger.warning("Photo too large (%d bytes), skipping", file.file_size)
        return None
    buffer = await bot.download_file(file.file_path)
    return buffer.read()


async def register_defect(
    defect_data: DefectData, employee: Employee, bot: Bot
) -> PersistResult:
    """Save defect, photos and measurements.
    Raises on the critical create_defect failure. Photo and measurement failures
    are non-critical: they are logged and skipped, never aborting the save.
    """
    saved_defect = await services.create_defect(defect_data, employee_id=employee.id)

    async def _fetch_photo(idx: int, file_id: str) -> bytes | None:
        """Download a photo and save it linked to the defect; None if it failed."""
        try:
            file_bytes = await _download_photo(bot, file_id)
            if file_bytes is None:
                return None
            await services.create_photo_from_bytes(
                defect_id=saved_defect.id,
                file_bytes=file_bytes,
                filename=f"bot_{saved_defect.id}_{idx + 1}_{file_id[-8:]}.jpg",
            )
        except Exception as exc:
            logger.warning("Photo save failed (idx=%d): %s", idx, exc, exc_info=True)
            return None
        else:
            return file_bytes

    photo_results = await asyncio.gather(
        *[_fetch_photo(i, fid) for i, fid in enumerate(defect_data.photo_file_ids)]
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


async def run_ai_analysis(
    defect_data: DefectData, defect_id: uuid.UUID, photo_bytes: list[bytes]
):
    """Run AI analysis and persist its result.
    Returns the AI result, or None if analysis failed. Never raises — a failure
    must not undo the already-saved defect.
    """
    try:
        ai_result = await asyncio.wait_for(
            analyze_defect(
                node=defect_data.node_label or "",
                defect_type=defect_data.defect_type_label or "",
                severity=defect_data.severity_label or "",
                description=defect_data.description,
                photos_bytes=photo_bytes or None,
            ),
            timeout=_ANALYSIS_TIMEOUT,
        )
    except TimeoutError:
        logger.warning(
            "AI analysis timed out after %.0fs for defect %s",
            _ANALYSIS_TIMEOUT,
            defect_id,
        )
        return None
    except Exception:
        logger.exception("AI analysis failed for defect %s", defect_id)
        return None

    if ai_result and ai_result.defect_class:
        try:
            await services.update_defect_ai_result(
                defect_id=defect_id,
                ai_class=ai_result.defect_class,
                ai_confidence=ai_result.confidence,
                ai_recommendation=ai_result.rag_recommendation,
                ai_verdict=ai_result.verdict,
            )
        except Exception:
            logger.warning(
                "Failed to persist AI result for defect %s", defect_id, exc_info=True
            )

    return ai_result
