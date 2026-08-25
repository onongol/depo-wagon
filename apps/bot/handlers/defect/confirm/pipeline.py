import asyncio
import logging
from dataclasses import dataclass

from telegram import Bot

from apps.ai_service.analysis import analyze_defect
from apps.bot import services
from apps.bot.user_data import DefectData
from apps.defects.validators import MAX_PHOTO_BYTES

logger = logging.getLogger(__name__)


@dataclass
class PersistResult:
    """Outcome of persisting a defect: the saved record and downloaded photo bytes."""

    defect: object
    photo_bytes: list[bytes]


async def register_defect(defect_data: DefectData, employee, bot: Bot) -> PersistResult:
    """Save defect, photos and measurements.
    Raises on the critical create_defect failure. Photo and measurement failures
    are non-critical: they are logged and skipped, never aborting the save.
    """
    saved_defect = await services.create_defect(
        wagon_id=defect_data.wagon_id,
        node=defect_data.node,
        defect_type=defect_data.defect_type,
        severity=defect_data.severity,
        description=defect_data.description,
        employee_id=employee.id if employee else None,
        department=defect_data.department or "",
        part_number=defect_data.part_number or "",
        responsible_employee_id=defect_data.responsible_employee_id,
    )

    async def _fetch_photo(idx: int, file_id: str) -> bytes | None:
        """
        Download a photo by file_id and save it linked to the defect.
        Returns the photo bytes, or None if failed.
        """
        try:
            file = await bot.get_file(file_id)
            if file.file_size and file.file_size > MAX_PHOTO_BYTES:
                logger.warning("Photo too large (%d bytes), skipping", file.file_size)
                return None

            file_bytes = bytes(await file.download_as_bytearray())
            filename = f"bot_{saved_defect.id}_{idx + 1}_{file_id[-8:]}.jpg"

            await services.create_photo_from_bytes(
                defect_id=saved_defect.id,
                file_bytes=file_bytes,
                filename=filename,
            )
            return file_bytes
        except Exception as exc:
            logger.warning("Photo save failed (idx=%d): %s", idx, exc)
            return None

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
            logger.warning("Measurements save failed: %s", exc)

    return PersistResult(defect=saved_defect, photo_bytes=all_photo_bytes)


async def run_ai_analysis(
    defect_data: DefectData, defect_id: str | int, photo_bytes: list[bytes]
):
    """Run AI analysis and persist its result.
    Returns the AI result, or None if analysis failed. Never raises — a failure
    must not undo the already-saved defect.
    """
    try:
        ai_result = await analyze_defect(
            node=defect_data.node_label or "",
            defect_type=defect_data.defect_type_label or "",
            severity=defect_data.severity_label or "",
            description=defect_data.description,
            photos_bytes=photo_bytes or None,
        )
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
            logger.warning("Failed to persist AI result for defect %s", defect_id)

    return ai_result
