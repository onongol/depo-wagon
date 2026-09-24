import html
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import UD_RESP_SEARCH
from apps.bot.keyboards.responsible_employee import responsible_employee_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.utils.pagination import clamp_page
from apps.bot.utils.screens import send_screen

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext

EMPLOYEE_PAGE_SIZE = 5


def _build_text(search: str, page: int, total: int, total_pages: int) -> str:
    if search:
        return str(M.ASK_RESPONSIBLE_EMPLOYEE_SEARCH).format(
            query=html.escape(search), count=total
        )
    return str(M.ASK_RESPONSIBLE_EMPLOYEE).format(
        page=page + 1, total=total_pages, count=total
    )


async def show_responsible_employee_list(
    send: Callable[..., Awaitable],
    state: FSMContext,
    department: str | None,
    page: int = 0,
) -> None:
    """Render one page of the department's employees matching the stored search.

    send is Message.answer (a new message) or Message.edit_text (in place).
    """
    search = (await state.get_data()).get(UD_RESP_SEARCH, "")

    total = await services.count_department_employees(department, search)
    total_pages, page = clamp_page(total, page, EMPLOYEE_PAGE_SIZE)
    employees = await services.get_department_employees(
        department, search, limit=EMPLOYEE_PAGE_SIZE, offset=page * EMPLOYEE_PAGE_SIZE
    )

    kb = responsible_employee_keyboard(employees, page, total_pages)
    text = _build_text(search, page, total, total_pages)

    await send_screen(send, text, parse_mode=M.PARSE_MODE, reply_markup=kb)
