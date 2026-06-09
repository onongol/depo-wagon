import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.callbacks import (
    DescSkipCB,
    ResponsibleEmployeePageCB,
    ResponsibleEmployeeSkipCB,
)
from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import RESP_EMP_PAGE_SIZE, responsible_employee_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DESC, RESPONSIBLE_EMPLOYEE
from apps.bot.user_data import DefectData

logger = logging.getLogger(__name__)

UD_RESP_EMPLOYEES = "_resp_employees"
UD_RESP_SEARCH = "_resp_search"


def _filter_and_page(all_employees: list, search: str, page: int):
    if search:
        filtered = [
            e
            for e in all_employees
            if search.lower() in f"{e.first_name} {e.last_name}".lower()
        ]
    else:
        filtered = all_employees

    total = len(filtered)
    total_pages = max(1, (total + RESP_EMP_PAGE_SIZE - 1) // RESP_EMP_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    page_employees = filtered[
        page * RESP_EMP_PAGE_SIZE : (page + 1) * RESP_EMP_PAGE_SIZE
    ]

    return page_employees, total, total_pages, page


def _build_text(search: str, page: int, total: int, total_pages: int) -> str:
    if search:
        return str(M.ASK_RESPONSIBLE_EMPLOYEE_SEARCH).format(query=search, count=total)
    return str(M.ASK_RESPONSIBLE_EMPLOYEE).format(
        page=page + 1, total=total_pages, count=total
    )


async def show_responsible_employee_list(
    msg_or_query,
    context: ContextTypes.DEFAULT_TYPE,
    page: int = 0,
    edit: bool = False,
) -> None:
    """Render the paginated employee list.

    msg_or_query: telegram Message (edit=False) or CallbackQuery (edit=True).
    """
    all_employees = context.user_data.get(UD_RESP_EMPLOYEES, [])
    search = context.user_data.get(UD_RESP_SEARCH, "")

    page_employees, total, total_pages, page = _filter_and_page(
        all_employees, search, page
    )
    kb = responsible_employee_keyboard(page_employees, page, total_pages)
    text = _build_text(search, page, total, total_pages)

    if edit:
        await msg_or_query.edit_message_text(
            text, parse_mode=M.PARSE_MODE, reply_markup=kb
        )
    else:
        await msg_or_query.reply_text(text, parse_mode=M.PARSE_MODE, reply_markup=kb)


async def receive_responsible_employee(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle employee selection, pagination, or skip."""
    query = update.callback_query
    await query.answer()

    cb = query.data

    if isinstance(cb, ResponsibleEmployeeSkipCB):
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

    if isinstance(cb, ResponsibleEmployeePageCB):
        await show_responsible_employee_list(query, context, page=cb.page, edit=True)
        return RESPONSIBLE_EMPLOYEE

    # ResponsibleEmployeeCB — employee selected
    employee_id = cb.employee_id
    try:
        from asgiref.sync import sync_to_async

        from apps.core.models import Employee

        get_emp = sync_to_async(
            lambda: Employee.objects.get(id=employee_id, is_active=True)
        )
        employee = await get_emp()
        label = f"{employee.first_name} {employee.last_name}"
    except Exception:
        label = str(employee_id)

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.responsible_employee_id = employee_id
    defect.responsible_employee_label = label
    context.user_data.pop(UD_RESP_EMPLOYEES, None)
    context.user_data.pop(UD_RESP_SEARCH, None)

    await query.edit_message_text(
        str(M.RESPONSIBLE_EMPLOYEE_CONFIRMED).format(label=label),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(DescSkipCB()),
    )
    return DESC


async def search_responsible_employee(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle text input as a search query for responsible employee."""
    context.user_data[UD_RESP_SEARCH] = update.message.text.strip()
    await show_responsible_employee_list(update.message, context, page=0, edit=False)
    return RESPONSIBLE_EMPLOYEE
