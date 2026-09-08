from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_DESC_SKIP
from apps.bot.constants import UD_RESP_EMPLOYEES, UD_RESP_SEARCH
from apps.bot.fsm import load_defect, load_employees, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

from .list import show_responsible_employee_list

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import (
        ResponsibleEmployeeCB,
        ResponsibleEmployeePageCB,
    )


async def _clear_roster(state: FSMContext) -> None:
    data = await state.get_data()
    data.pop(UD_RESP_EMPLOYEES, None)
    data.pop(UD_RESP_SEARCH, None)
    await state.set_data(data)


async def skip_responsible_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Record no responsible employee and move on to the description."""
    await callback.answer()

    defect = await load_defect(state)
    defect.responsible_employee_id = None
    defect.responsible_employee_label = None
    await save_defect(state, defect)
    await _clear_roster(state)

    await callback.message.edit_text(
        str(M.ASK_DESCRIPTION),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(CB_DESC_SKIP),
    )
    await state.set_state(DefectSG.desc)


async def page_responsible_employee(
    callback: CallbackQuery, callback_data: ResponsibleEmployeePageCB, state: FSMContext
) -> None:
    """Re-render the employee list at another page."""
    await callback.answer()

    await show_responsible_employee_list(
        callback.message.edit_text, state, page=callback_data.page, edit=True
    )


async def select_responsible_employee(
    callback: CallbackQuery, callback_data: ResponsibleEmployeeCB, state: FSMContext
) -> None:
    """Record the chosen employee and move on to the description."""
    await callback.answer()

    employee_id = callback_data.employee_id
    employees = await load_employees(state)
    employee = next((emp for emp in employees if emp.id == employee_id), None)
    label = (
        f"{employee.first_name} {employee.last_name}" if employee else str(employee_id)
    )

    defect = await load_defect(state)
    defect.responsible_employee_id = employee_id
    defect.responsible_employee_label = label
    await save_defect(state, defect)
    await _clear_roster(state)

    await callback.message.edit_text(
        str(M.RESPONSIBLE_EMPLOYEE_CONFIRMED).format(label=label),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(CB_DESC_SKIP),
    )
    await state.set_state(DefectSG.desc)
