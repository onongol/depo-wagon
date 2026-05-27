import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot import services
from apps.bot.handlers.employee import get_employee
from apps.bot.messages import BotMessages as M

from .constants import PAGE_SIZE
from .keyboards import status_picker_keyboard, tasks_keyboard
from .text import build_text

logger = logging.getLogger(__name__)


async def show_status_picker(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Replace keyboard with status options for a specific defect."""
    query = update.callback_query
    await query.answer()

    # callback_data: "status_pick:<defect_id>:<page>"
    _, defect_id, page = query.data.split(":")

    await query.edit_message_reply_markup(
        reply_markup=status_picker_keyboard(defect_id, page)
    )


async def set_defect_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save new status and refresh the defect list."""
    query = update.callback_query
    await query.answer()

    # callback_data: "status_set:<defect_id>:<status>:<page>"
    _, defect_id, status, page = query.data.split(":")
    page = int(page)

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
