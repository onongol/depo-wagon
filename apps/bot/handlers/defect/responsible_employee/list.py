import html
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.keyboards.responsible_employee import responsible_employee_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.utils.pagination import clamp_page

if TYPE_CHECKING:
    from apps.bot.handlers.defect.scene import Screen

EMPLOYEE_PAGE_SIZE = 5


def _build_text(search: str, page: int, total: int, total_pages: int) -> str:
    if search:
        return str(M.ASK_RESPONSIBLE_EMPLOYEE_SEARCH).format(
            query=html.escape(search), count=total
        )
    return str(M.ASK_RESPONSIBLE_EMPLOYEE).format(
        page=page + 1, total=total_pages, count=total
    )


async def employee_list_screen(
    department: str | None, search: str, page: int = 0
) -> Screen:
    """One page of the department's employees matching the search."""
    total = await services.count_department_employees(department, search)
    total_pages, page = clamp_page(total, page, EMPLOYEE_PAGE_SIZE)
    employees = await services.get_department_employees(
        department, search, limit=EMPLOYEE_PAGE_SIZE, offset=page * EMPLOYEE_PAGE_SIZE
    )

    text = _build_text(search, page, total, total_pages)
    return text, responsible_employee_keyboard(employees, page, total_pages)
