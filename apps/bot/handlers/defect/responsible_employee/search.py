from typing import TYPE_CHECKING

from apps.bot.constants import UD_RESP_SEARCH
from apps.bot.fsm import load_defect

from .list import show_responsible_employee_list

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message


async def search_responsible_employee(message: Message, state: FSMContext) -> None:
    """Handle text input as a search query for responsible employee.

    Re-renders from page 0 as a new message, leaving the state where it is.
    """
    defect = await load_defect(state)

    await state.update_data({UD_RESP_SEARCH: message.text.strip()})
    await show_responsible_employee_list(
        message.answer, state, defect.department, page=0
    )
