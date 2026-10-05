import logging
from typing import TYPE_CHECKING

from apps.bot.handlers.defect.notifications import notify_decommission
from apps.defects.constants import DefectVerdict

if TYPE_CHECKING:
    from apps.bot.user_data import DefectData
    from apps.core.models import Employee

logger = logging.getLogger(__name__)


async def alert_decommission(employee: Employee, defect_data: DefectData) -> None:
    """Alert managers to a decommission verdict; a failure must not stop the AI."""
    if defect_data.verdict != DefectVerdict.DECOMMISSION:
        return
    try:
        await notify_decommission(employee, defect_data)
    except Exception:
        logger.exception("Decommission alert failed for %s", defect_data.defect_id)
