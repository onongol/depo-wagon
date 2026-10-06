from functools import partial
from typing import TYPE_CHECKING

from apps.bot.utils.screens import edit_or_send
from apps.bot.utils.unregistered import refuse_unregistered

from .render import render_page

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

    from apps.bot.callback_data import TasksPageCB
    from apps.core.models import Employee


async def my_tasks(
    message: Message, state: FSMContext, employee: Employee | None
) -> None:
    """Show the first page of open defects, leaving the AI chat or support prompt."""
    if not employee:
        await refuse_unregistered(message)
        return

    await state.clear()
    await render_page(message.answer, employee, page=0)


async def my_tasks_page(
    callback: CallbackQuery, callback_data: TasksPageCB, employee: Employee | None
) -> None:
    """Turn to another page of the list."""
    if not employee:
        await refuse_unregistered(callback)
        return

    await callback.answer()
    await render_page(
        partial(edit_or_send, callback), employee, page=callback_data.page
    )
