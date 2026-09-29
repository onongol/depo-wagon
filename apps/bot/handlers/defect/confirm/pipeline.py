import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from apps.ai_service.analysis import analyze_defect
from apps.bot import services
from apps.bot.fsm import save_defect
from apps.bot.handlers.defect.notifications import notify_decommission
from apps.defects.constants import DefectVerdict

if TYPE_CHECKING:
    import uuid

    from aiogram import Bot
    from aiogram.fsm.context import FSMContext

    from apps.bot.user_data import DefectData
    from apps.core.models import Employee

logger = logging.getLogger(__name__)

_ANALYSIS_TIMEOUT = 60.0
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


async def persist_defect(
    state: FSMContext, defect_data: DefectData, employee: Employee, bot: Bot
) -> PersistResult:
    """Save the defect and record its id in the form; raises as register_defect does."""
    registered = await register_defect(defect_data, employee, bot)
    defect_data.defect_id = str(registered.defect.id)
    await save_defect(state, defect_data)
    return registered


async def alert_decommission(
    bot: Bot, employee: Employee, defect_data: DefectData
) -> None:
    """Alert managers to a decommission verdict; a failure must not stop the AI."""
    if defect_data.verdict != DefectVerdict.DECOMMISSION:
        return
    try:
        await notify_decommission(bot, employee, defect_data)
    except Exception:
        logger.exception("Decommission alert failed for %s", defect_data.defect_id)


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
