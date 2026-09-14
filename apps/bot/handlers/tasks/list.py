import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import (
    ROLES_CHANGING_OWN_STATUS,
    TASKS_PAGE_SIZE,
)
from apps.bot.handlers.employee import get_employee
from apps.bot.keyboards.tasks import tasks_keyboard
from apps.bot.messages import BotMessages as M
from apps.core.constants import ROLES_WITH_ALL_DEFECTS

from .text import build_text

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import CallbackQuery, Message

    from apps.bot.callback_data import TasksPageCB

logger = logging.getLogger(__name__)


def can_change_status(employee) -> bool:
    return employee.role in ROLES_WITH_ALL_DEFECTS | ROLES_CHANGING_OWN_STATUS


async def render_page(send: Callable[..., Awaitable], employee, page: int) -> None:
    """Fetch one page of open defects and hand it to send."""
    offset = page * TASKS_PAGE_SIZE

    if employee.role in ROLES_WITH_ALL_DEFECTS:
        total = await services.get_all_open_defects_count()
        defects = await services.get_all_open_defects(
            limit=TASKS_PAGE_SIZE, offset=offset
        )
    else:
        total = await services.get_open_defects_count(employee_id=employee.id)
        defects = await services.get_open_defects(
            employee_id=employee.id, limit=TASKS_PAGE_SIZE, offset=offset
        )

    if not defects:
        await send(str(M.NO_TASKS), parse_mode=M.PARSE_MODE)
        return

    await send(
        build_text(defects, page, total),
        parse_mode=M.PARSE_MODE,
        reply_markup=tasks_keyboard(
            defects, page, total, can_change_status=can_change_status(employee)
        ),
    )


async def my_tasks(message: Message) -> None:
    """Show the first page of open defects."""
    employee = await get_employee(message.from_user.id)

    if not employee:
        await message.answer(str(M.NOT_REGISTERED), parse_mode=M.PARSE_MODE)
        return

    await render_page(message.answer, employee, page=0)


async def my_tasks_page(callback: CallbackQuery, callback_data: TasksPageCB) -> None:
    """Turn to another page of the list."""
    await callback.answer()

    employee = await get_employee(callback.from_user.id)
    if not employee:
        await callback.message.edit_text(str(M.NOT_REGISTERED), parse_mode=M.PARSE_MODE)
        return

    await render_page(callback.message.edit_text, employee, page=callback_data.page)
