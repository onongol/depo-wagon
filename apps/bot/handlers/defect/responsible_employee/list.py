import html
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramBadRequest

from apps.bot import services
from apps.bot.constants import UD_RESP_SEARCH
from apps.bot.keyboards.defect import responsible_employee_keyboard
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext

EMPLOYEE_PAGE_SIZE = 5


def _clamp_page(total: int, page: int) -> tuple[int, int]:
    """Number of pages, never less than one, and page pulled into range."""
    total_pages = max(1, (total + EMPLOYEE_PAGE_SIZE - 1) // EMPLOYEE_PAGE_SIZE)
    return total_pages, max(0, min(page, total_pages - 1))


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
    *,
    edit: bool = False,
) -> None:
    """Render one page of the department's employees matching the stored search.

    send is Message.answer (a new message) or Message.edit_text (in place).
    """
    search = (await state.get_data()).get(UD_RESP_SEARCH, "")

    total = await services.count_department_employees(department, search)
    total_pages, page = _clamp_page(total, page)
    employees = await services.get_department_employees(
        department, search, limit=EMPLOYEE_PAGE_SIZE, offset=page * EMPLOYEE_PAGE_SIZE
    )

    kb = responsible_employee_keyboard(employees, page, total_pages)
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
