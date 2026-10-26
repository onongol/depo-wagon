import asyncio
import logging
from typing import TYPE_CHECKING

from apps.ai_service.analysis import analyze_defect
from apps.bot import services
from apps.bot.constants import SEVERITY_EMOJI
from apps.bot.utils.choices import choice_label, emoji_label
from apps.defects.constants import DefectNode, DefectSeverity, DefectType

if TYPE_CHECKING:
    import uuid

    from apps.bot.user_data import DefectData

logger = logging.getLogger(__name__)

_ANALYSIS_TIMEOUT = 60.0


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
                node=choice_label(DefectNode, defect_data.node),
                defect_type=choice_label(DefectType, defect_data.defect_type),
                severity=emoji_label(
                    SEVERITY_EMOJI, DefectSeverity, defect_data.severity
                ),
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
