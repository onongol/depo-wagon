import asyncio
import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError

from apps.bot import services
from apps.bot.handlers.defect.text import build_decommission_alert_text

if TYPE_CHECKING:
    from aiogram import Bot

    from apps.bot.user_data import DefectData
    from apps.core.models import Employee

logger = logging.getLogger(__name__)


async def notify_decommission(
    bot: Bot,
    employee: Employee,
    defect: DefectData,
) -> None:
    """Send decommission alert to all managers and engineers in parallel."""
    managers = await services.get_managers_and_engineers()
    if not managers:
        return

    text = build_decommission_alert_text(defect, employee)

    async def _send_one(manager) -> None:
        try:
            await bot.send_message(chat_id=manager.telegram_id, **text.as_kwargs())
        except TelegramAPIError as exc:
            logger.warning("Failed to notify employee %s: %s", manager.id, exc)

    await asyncio.gather(*[_send_one(manager) for manager in managers])
