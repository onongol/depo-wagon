from functools import partial
from typing import TYPE_CHECKING

from aiogram import flags

from apps.bot.utils.screens import edit_or_send

from .render import render_page

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

    from apps.bot.callback_data import TasksPageCB
    from apps.core.models import Employee


@flags.registered
async def my_tasks(message: Message, state: FSMContext, employee: Employee) -> None:
    """Show the first page of open defects, leaving the AI chat or support prompt."""
    await state.clear()
    await render_page(message.answer, employee, page=0)


@flags.registered
async def my_tasks_page(
    callback: CallbackQuery, callback_data: TasksPageCB, employee: Employee
) -> None:
    """Turn to another page of the list."""
    await callback.answer()
    await render_page(
        partial(edit_or_send, callback), employee, page=callback_data.page
    )
