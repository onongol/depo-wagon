from telegram import CallbackQuery, Message
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from apps.bot.keyboards.defect import RESP_EMP_PAGE_SIZE, responsible_employee_keyboard
from apps.bot.messages import BotMessages as M

UD_RESP_EMPLOYEES = "_resp_employees"
UD_RESP_SEARCH = "_resp_search"


def _filter_and_page(all_employees: list, search: str, page: int) -> tuple:
    if search:
        search_query = search.lower()
        filtered = [
            emp
            for emp in all_employees
            if search_query in f"{emp.first_name} {emp.last_name}".lower()
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
    msg_or_query: Message | CallbackQuery,
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
        try:
            await msg_or_query.edit_message_text(
                text, parse_mode=M.PARSE_MODE, reply_markup=kb
            )
        except BadRequest as exc:
            if "Message is not modified" not in str(exc):
                raise
    else:
        await msg_or_query.reply_text(text, parse_mode=M.PARSE_MODE, reply_markup=kb)
