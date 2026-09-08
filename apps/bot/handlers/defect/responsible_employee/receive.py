from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_DESC_SKIP
from apps.bot.constants import UD_DEFECT, UD_RESP_EMPLOYEES, UD_RESP_SEARCH
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DESC, RESPONSIBLE_EMPLOYEE

from .list import show_responsible_employee_list

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

    from apps.bot.user_data import DefectData


def _clear_roster(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(UD_RESP_EMPLOYEES, None)
    context.user_data.pop(UD_RESP_SEARCH, None)


async def skip_responsible_employee(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Record no responsible employee and move on to the description."""
    query = update.callback_query
    await query.answer()

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.responsible_employee_id = None
    defect.responsible_employee_label = None
    _clear_roster(context)

    await query.edit_message_text(
        str(M.ASK_DESCRIPTION),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(CB_DESC_SKIP),
    )
    return DESC


async def page_responsible_employee(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Re-render the employee list at another page."""
    query = update.callback_query
    await query.answer()

    await show_responsible_employee_list(
        query, context, page=query.data.page, edit=True
    )
    return RESPONSIBLE_EMPLOYEE


async def select_responsible_employee(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Record the chosen employee and move on to the description."""
    query = update.callback_query
    await query.answer()

    employee_id = query.data.employee_id
    employees = context.user_data.get(UD_RESP_EMPLOYEES, [])
    employee = next((emp for emp in employees if emp.id == employee_id), None)
    label = (
        f"{employee.first_name} {employee.last_name}" if employee else str(employee_id)
    )

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.responsible_employee_id = employee_id
    defect.responsible_employee_label = label
    _clear_roster(context)

    await query.edit_message_text(
        str(M.RESPONSIBLE_EMPLOYEE_CONFIRMED).format(label=label),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(CB_DESC_SKIP),
    )
    return DESC
