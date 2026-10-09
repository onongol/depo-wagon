from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import DefectTypeCB
from apps.bot.constants import FSMKey
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import defect_type_keyboard
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

from .scene import DefectScene
from .text import build_ask_defect_type_text, build_edit_defect_type_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen


class DefectTypeScene(DefectScene, state=DefectSG.defect_type.state):
    """The defect type, from buttons; a human factor asks for the employee next."""

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        return DefectSG.part_number

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        keyboard = defect_type_keyboard()
        if data.get(FSMKey.EDITING):
            return build_edit_defect_type_text(), keyboard
        return build_ask_defect_type_text(), keyboard

    @on.callback_query(DefectTypeCB.filter())
    async def receive(
        self, callback: CallbackQuery, callback_data: DefectTypeCB, state: FSMContext
    ) -> None:
        """A human factor with no employee yet asks for one next, from Edit too.

        That list is a lookup: if it fails, the state stays here for these buttons.
        """
        await callback.answer()

        dtype_value = callback_data.value
        human_factor = dtype_value == DefectType.HUMAN_FACTOR

        defect = await load_defect(state)
        defect.defect_type = dtype_value

        if not human_factor:
            defect.responsible_employee_id = None
            defect.responsible_employee_label = None
        await save_defect(state, defect)

        if not human_factor or defect.responsible_employee_id:
            await self.go_on(state, DefectSG.photo)
            return

        try:
            await self.wizard.goto(DefectSG.responsible_employee)
        except Exception:
            await state.set_state(DefectSG.defect_type)
            raise
