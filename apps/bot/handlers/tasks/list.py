import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot import services
from apps.bot.constants import PAGE_SIZE
from apps.bot.handlers.employee import get_employee
from apps.bot.keyboards.tasks import tasks_keyboard
from apps.bot.messages import BotMessages as M

from .text import build_text

logger = logging.getLogger(__name__)


async def my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show paginated list of open defects for the current employee."""
    employee = await get_employee(update, context)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        page = query.data.page
        send = query.edit_message_text
    else:
        if not employee:
            await update.message.reply_text(
                str(M.NOT_REGISTERED), parse_mode=M.PARSE_MODE
            )
            return
        page = 0
        send = update.message.reply_text

    employee_id = employee.id if employee else None
    offset = page * PAGE_SIZE
    total = await services.get_open_defects_count(employee_id=employee_id)
    defects = await services.get_open_defects(
        limit=PAGE_SIZE, offset=offset, employee_id=employee_id
    )

    if not defects:
        await send(str(M.NO_TASKS), parse_mode=M.PARSE_MODE)
        return

    await send(
        build_text(defects, page, total),
        parse_mode=M.PARSE_MODE,
        reply_markup=tasks_keyboard(defects, page, total),
    )
