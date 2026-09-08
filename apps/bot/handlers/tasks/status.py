import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.handlers.employee import get_employee
from apps.bot.keyboards.tasks import status_picker_keyboard

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

    await services.update_defect_status(callback_data.defect_id, callback_data.status)

    employee = await get_employee(callback.from_user.id)
    await render_page(callback.message.edit_text, employee, page=callback_data.page)
