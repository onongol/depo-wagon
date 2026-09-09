from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramBadRequest

from apps.bot.constants import UD_RESP_SEARCH
from apps.bot.fsm import load_employees
from apps.bot.keyboards.defect import responsible_employee_keyboard
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext

EMPLOYEE_PAGE_SIZE = 5


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
    total_pages = max(1, (total + EMPLOYEE_PAGE_SIZE - 1) // EMPLOYEE_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    page_employees = filtered[
        page * EMPLOYEE_PAGE_SIZE : (page + 1) * EMPLOYEE_PAGE_SIZE
    ]

    return page_employees, total, total_pages, page


def _build_text(search: str, page: int, total: int, total_pages: int) -> str:
    if search:
        return str(M.ASK_RESPONSIBLE_EMPLOYEE_SEARCH).format(query=search, count=total)
    return str(M.ASK_RESPONSIBLE_EMPLOYEE).format(
        page=page + 1, total=total_pages, count=total
    )


async def show_responsible_employee_list(
    send: Callable[..., Awaitable],
    state: FSMContext,
    page: int = 0,
    *,
    edit: bool = False,
) -> None:
    """Render the paginated employee list.

    send is Message.answer (a new message) or Message.edit_text (in place).
    """
    all_employees = await load_employees(state)
    search = (await state.get_data()).get(UD_RESP_SEARCH, "")

    page_employees, total, total_pages, page = _filter_and_page(
        all_employees, search, page
    )

    kb = responsible_employee_keyboard(page_employees, page, total_pages)
    text = _build_text(search, page, total, total_pages)

    try:
        await send(text, parse_mode=M.PARSE_MODE, reply_markup=kb)
    except TelegramBadRequest as exc:
        # Re-rendering the same page is a no-op Telegram rejects. PTB
        # normalised this text; aiogram passes Telegram's own wording through,
        # which is lower case — matching on the old string would never hit and
        # every idle re-render would raise.
        if not edit or "message is not modified" not in exc.message.lower():
            raise
