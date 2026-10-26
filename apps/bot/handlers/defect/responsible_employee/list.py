from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.handlers.defect.text import (
    build_ask_responsible_employee_text,
    build_responsible_employee_search_text,
)
from apps.bot.keyboards.responsible_employee import responsible_employee_keyboard
from apps.bot.utils.pagination import clamp_page

if TYPE_CHECKING:
    from apps.bot.handlers.defect.scene import Screen

EMPLOYEE_PAGE_SIZE = 5


async def employee_list_screen(
    department: str | None, search: str, page: int = 0
) -> Screen:
    """One page of the department's employees matching the search."""
    total = await services.count_department_employees(department, search)
    total_pages, page = clamp_page(total, page, EMPLOYEE_PAGE_SIZE)

    employees = await services.get_department_employees(
        department, search, limit=EMPLOYEE_PAGE_SIZE, offset=page * EMPLOYEE_PAGE_SIZE
    )

    if search:
        text = build_responsible_employee_search_text(search, total)
    else:
        text = build_ask_responsible_employee_text(page + 1, total_pages, total)

    keyboard = responsible_employee_keyboard(
        employees, page, total_pages, searching=bool(search)
    )
    return text, keyboard
