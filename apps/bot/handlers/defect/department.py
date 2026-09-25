from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import DepartmentCB
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import department_keyboard, node_keyboard_for_department
from apps.bot.states import DefectSG
from apps.core.constants import Department

from .scene import DefectScene
from .text import build_department_confirmed_text, build_wagon_confirmed_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen

_DEPT_LABELS = dict(Department.choices)


class DepartmentScene(DefectScene, state=DefectSG.department.state):
    """The department, picked from buttons; the summary has no edit for it."""

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        return build_wagon_confirmed_text(form.wagon_number), department_keyboard()

    @on.callback_query(DepartmentCB.filter())
    async def receive(
        self, callback: CallbackQuery, callback_data: DepartmentCB, state: FSMContext
    ) -> None:
        await callback.answer()

        dept_value = callback_data.value
        dept_label = str(_DEPT_LABELS.get(dept_value, dept_value))

        defect = await load_defect(state)
        defect.department = dept_value
        defect.department_label = dept_label
        await save_defect(state, defect)

        await callback.message.edit_text(
            **build_department_confirmed_text(dept_label).as_kwargs(),
            reply_markup=node_keyboard_for_department(dept_value),
        )
        await state.set_state(DefectSG.node)
