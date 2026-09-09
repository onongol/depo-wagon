import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import TASKS_PAGE_SIZE
from apps.bot.handlers.employee import get_employee
from apps.bot.keyboards.tasks import tasks_keyboard
from apps.bot.messages import BotMessages as M

from .text import build_text

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import CallbackQuery, Message

    from apps.bot.callback_data import TasksPageCB

logger = logging.getLogger(__name__)


async def render_page(send: Callable[..., Awaitable], employee, page: int) -> None:
    """Fetch one page of open defects and hand it to send.

    send is either Message.answer or Message.edit_text — the list is a fresh
    message when it comes from a command and an edit when it comes from a page
    button, which is what PTB did by switching on update.callback_query.
    """
    employee_id = employee.id if employee else None
    total = await services.get_open_defects_count(employee_id=employee_id)
    defects = await services.get_open_defects(
        limit=TASKS_PAGE_SIZE, offset=page * TASKS_PAGE_SIZE, employee_id=employee_id
    )

    if not defects:
        await send(str(M.NO_TASKS), parse_mode=M.PARSE_MODE)
        return

    await send(
        build_text(defects, page, total),
        parse_mode=M.PARSE_MODE,
        reply_markup=tasks_keyboard(defects, page, total),
    )


async def my_tasks(message: Message) -> None:
    """Show the first page of open defects."""
    employee = await get_employee(message.from_user.id)

    if not employee:
        await message.answer(str(M.NOT_REGISTERED), parse_mode=M.PARSE_MODE)
        return

    await render_page(message.answer, employee, page=0)


async def my_tasks_page(callback: CallbackQuery, callback_data: TasksPageCB) -> None:
    """Turn to another page of the list.

    No unregistered guard, matching PTB: reaching this needs a keyboard that
    was rendered for a registered employee in the first place.
    """
    await callback.answer()

    employee = await get_employee(callback.from_user.id)
    await render_page(callback.message.edit_text, employee, page=callback_data.page)
