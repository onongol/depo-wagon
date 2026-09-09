from typing import TYPE_CHECKING

from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import node_keyboard_for_department
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.core.constants import Department

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import DepartmentCB

_DEPT_LABELS = dict(Department.choices)


async def receive_department(
    callback: CallbackQuery, callback_data: DepartmentCB, state: FSMContext
) -> None:
    """Handle department selection from inline keyboard."""
    await callback.answer()

    dept_value = callback_data.value
    dept_label = str(_DEPT_LABELS.get(dept_value, dept_value))

    defect = await load_defect(state)
    defect.department = dept_value
    defect.department_label = dept_label
    await save_defect(state, defect)

    await callback.message.edit_text(
        str(M.DEPARTMENT_CONFIRMED).format(label=dept_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=node_keyboard_for_department(dept_value),
    )
    await state.set_state(DefectSG.node)
