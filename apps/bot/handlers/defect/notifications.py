import asyncio
import html
import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError

from apps.bot import services
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram import Bot

    from apps.bot.user_data import DefectData

logger = logging.getLogger(__name__)


async def notify_decommission(
    bot: Bot,
    employee,
    defect: DefectData | None,
) -> None:
    """Send decommission alert to all managers and engineers in parallel."""
    managers = await services.get_managers_and_engineers()
    if not managers:
        return

    text = str(M.DECOMMISSION_ALERT).format(
        wagon_number=html.escape(str(defect.wagon_number)) if defect else "?",
        node_label=html.escape(str(defect.node_label)) if defect else "?",
        defect_type_label=html.escape(str(defect.defect_type_label)) if defect else "?",
        inspector_name=html.escape(employee.full_name) if employee else "—",
    )

    async def _send_one(manager) -> None:
        try:
            await bot.send_message(
                chat_id=manager.telegram_id,
                text=text,
                parse_mode=M.PARSE_MODE,
            )
        except TelegramAPIError as exc:
            logger.warning(
                "Failed to notify manager %s (tg=%s): %s",
                manager.full_name,
                manager.telegram_id,
                exc,
            )

    await asyncio.gather(*[_send_one(manager) for manager in managers])
