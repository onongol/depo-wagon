from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import TASKS_PAGE_SIZE
from apps.bot.keyboards.tasks import tasks_keyboard
from apps.bot.utils.pagination import clamp_page

from .text import build_no_tasks_text, build_text_list

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


async def render_page(send: Callable[..., Awaitable], employee, page: int) -> None:
    """Fetch one page of open defects and hand it to send."""
    total = await services.get_open_defects_count(employee=employee)
    pages, page = clamp_page(total, page, TASKS_PAGE_SIZE)

    defects = await services.get_open_defects(
        employee=employee, limit=TASKS_PAGE_SIZE, offset=page * TASKS_PAGE_SIZE
    )

    if not defects:
        await send(**build_no_tasks_text().as_kwargs())
        return

    await send(
        **build_text_list(defects, page, total, pages).as_kwargs(),
        reply_markup=tasks_keyboard(defects, page, pages),
    )
