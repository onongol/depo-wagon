from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.handlers.defect.text import build_decommission_alert_text

if TYPE_CHECKING:
    from apps.bot.user_data import DefectData
    from apps.core.models import Employee


async def notify_decommission(employee: Employee, defect: DefectData) -> None:
    """Queue the decommission alert for every manager and engineer."""
    managers = await services.get_managers_and_engineers()
    if not managers:
        return

    text = build_decommission_alert_text(defect, employee)
    await services.queue_messages([manager.id for manager in managers], text)
