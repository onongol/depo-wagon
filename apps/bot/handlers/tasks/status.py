import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import PAGE_SIZE
from apps.bot.handlers.employee import get_employee
from apps.bot.keyboards.tasks import status_picker_keyboard, tasks_keyboard
from apps.bot.messages import BotMessages as M

from .text import build_text

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def show_status_picker(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Replace keyboard with status options for a specific defect."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_reply_markup(
        reply_markup=status_picker_keyboard(query.data.defect_id, query.data.page)
    )


async def set_defect_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save new status and refresh the defect list."""
    query = update.callback_query
    await query.answer()

    defect_id = query.data.defect_id
    status = query.data.status
    page = query.data.page

    await services.update_defect_status(defect_id, status)

    employee = await get_employee(update, context)
    employee_id = employee.id if employee else None
    offset = page * PAGE_SIZE
    total = await services.get_open_defects_count(employee_id=employee_id)
    defects = await services.get_open_defects(
        limit=PAGE_SIZE, offset=offset, employee_id=employee_id
    )

    if not defects:
        await query.edit_message_text(
            str(M.NO_TASKS),
            parse_mode=M.PARSE_MODE,
        )
        return

    await query.edit_message_text(
        build_text(defects, page, total),
        parse_mode=M.PARSE_MODE,
        reply_markup=tasks_keyboard(defects, page, total),
    )
