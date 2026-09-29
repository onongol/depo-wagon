from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import DepartmentCB
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import department_keyboard
from apps.bot.states import DefectSG
from apps.core.constants import Department

from .scene import DefectScene
from .text import build_ask_department_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen

_DEPT_LABELS = dict(Department.choices)


class DepartmentScene(DefectScene, state=DefectSG.department.state):
    """The department, picked from buttons; the summary has no edit for it."""

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        return DefectSG.wagon_num

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        return build_ask_department_text(), department_keyboard()

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

        await self.wizard.goto(DefectSG.node)
