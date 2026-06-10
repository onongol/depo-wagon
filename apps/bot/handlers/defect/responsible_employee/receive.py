from telegram import CallbackQuery, Update
from telegram.ext import ContextTypes

from apps.bot.callbacks import (
    DescSkipCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    ResponsibleEmployeeSkipCB,
)
from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DESC, RESPONSIBLE_EMPLOYEE
from apps.bot.user_data import DefectData

from .list import UD_RESP_EMPLOYEES, UD_RESP_SEARCH, show_responsible_employee_list


async def _handle_skip(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> int:
    defect: DefectData = context.user_data[UD_DEFECT]
    defect.responsible_employee_id = None
    defect.responsible_employee_label = None
    context.user_data.pop(UD_RESP_EMPLOYEES, None)
    context.user_data.pop(UD_RESP_SEARCH, None)

    await query.edit_message_text(
        str(M.ASK_DESCRIPTION),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(DescSkipCB()),
    )
    return DESC


async def _handle_page(
    query: CallbackQuery,
    cb: ResponsibleEmployeePageCB,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    await show_responsible_employee_list(query, context, page=cb.page, edit=True)
    return RESPONSIBLE_EMPLOYEE


async def _handle_select(
    query: CallbackQuery, cb: ResponsibleEmployeeCB, context: ContextTypes.DEFAULT_TYPE
) -> int:
    employees = context.user_data.get(UD_RESP_EMPLOYEES, [])
    employee = next((emp for emp in employees if emp.id == cb.employee_id), None)
    label = (
        f"{employee.first_name} {employee.last_name}"
        if employee
        else str(cb.employee_id)
    )

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.responsible_employee_id = cb.employee_id
    defect.responsible_employee_label = label
    context.user_data.pop(UD_RESP_EMPLOYEES, None)
    context.user_data.pop(UD_RESP_SEARCH, None)

    await query.edit_message_text(
        str(M.RESPONSIBLE_EMPLOYEE_CONFIRMED).format(label=label),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(DescSkipCB()),
    )
    return DESC


async def receive_responsible_employee(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Dispatch employee callback to skip / page / select handler."""
    query = update.callback_query
    await query.answer()
    cb = query.data

    if isinstance(cb, ResponsibleEmployeeSkipCB):
        return await _handle_skip(query, context)
    if isinstance(cb, ResponsibleEmployeePageCB):
        return await _handle_page(query, cb, context)
    return await _handle_select(query, cb, context)
