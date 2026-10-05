import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.handlers.defect.text import build_decommission_alert_text
from apps.defects.constants import DefectVerdict

if TYPE_CHECKING:
    from apps.bot.user_data import DefectData
    from apps.core.models import Employee

logger = logging.getLogger(__name__)


async def alert_decommission(employee: Employee, defect_data: DefectData) -> None:
    """Queue the alert for every manager and engineer; a failure must not stop the AI."""
    if defect_data.verdict != DefectVerdict.DECOMMISSION:
        return
    try:
        managers = await services.get_managers_and_engineers()
        if managers:
            text = build_decommission_alert_text(defect_data, employee)
            await services.queue_messages([manager.id for manager in managers], text)
    except Exception:
        logger.exception("Decommission alert failed for %s", defect_data.defect_id)
