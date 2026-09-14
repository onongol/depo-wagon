import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.handlers.employee import get_employee
from apps.bot.keyboards.tasks import status_picker_keyboard
from apps.bot.messages import BotMessages as M

from .list import render_page

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import StatusPickCB, StatusSetCB

logger = logging.getLogger(__name__)


async def show_status_picker(
    callback: CallbackQuery, callback_data: StatusPickCB
) -> None:
    """Replace keyboard with status options for a specific defect."""
    await callback.answer()

    await callback.message.edit_reply_markup(
        reply_markup=status_picker_keyboard(callback_data.defect_id, callback_data.page)
    )


async def set_defect_status(
    callback: CallbackQuery, callback_data: StatusSetCB
) -> None:
    """Save new status and refresh the defect list."""
    await callback.answer()

    employee = await get_employee(callback.from_user.id)
    if not employee:
        await callback.message.edit_text(str(M.NOT_REGISTERED), parse_mode=M.PARSE_MODE)
        return

    try:
        saved = await services.update_defect_status(
            callback_data.defect_id, callback_data.status
        )
    except Exception:
        logger.exception("Failed to set status on defect %s", callback_data.defect_id)
        await callback.message.answer(
            str(M.STATUS_CHANGE_FAILED), parse_mode=M.PARSE_MODE
        )
        return

    if not saved:
        await callback.message.answer(
            str(M.STATUS_DEFECT_MISSING), parse_mode=M.PARSE_MODE
        )

    await render_page(callback.message.edit_text, employee, page=callback_data.page)
