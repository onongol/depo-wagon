from typing import TYPE_CHECKING

from apps.bot.messages import BotMessages as M

from .render import render_page
from .utils import refuse_unregistered

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message

    from apps.bot.callback_data import TasksPageCB
    from apps.core.models import Employee


async def my_tasks(message: Message, employee: Employee | None) -> None:
    """Show the first page of open defects."""
    if not employee:
        await message.answer(str(M.NOT_REGISTERED), parse_mode=M.PARSE_MODE)
        return

    await render_page(message.answer, employee, page=0)


async def my_tasks_page(
    callback: CallbackQuery, callback_data: TasksPageCB, employee: Employee | None
) -> None:
    """Turn to another page of the list."""
    if not employee:
        await refuse_unregistered(callback)
        return

    await callback.answer()
    await render_page(callback.message.edit_text, employee, page=callback_data.page)
