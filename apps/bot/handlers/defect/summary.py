from typing import TYPE_CHECKING, Any

from aiogram import F
from aiogram.fsm.scene import on

from apps.bot.callback_data import ConfirmCB, EditCB
from apps.bot.constants import EDIT_RESPONSIBLE, UD_EDITING
from apps.bot.fsm import drop_keys, load_defect
from apps.bot.keyboards.confirm import confirm_keyboard
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

from .confirm import confirm_defect
from .scene import DefectScene
from .text import build_summary_text

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

    from apps.bot.user_data import DefectData
    from apps.core.models import Employee

    from .scene import Screen

_EDIT_SCENES = {
    "wagon": DefectSG.wagon_num,
    "node": DefectSG.node,
    "part_number": DefectSG.part_number,
    "defect_type": DefectSG.defect_type,
    EDIT_RESPONSIBLE: DefectSG.responsible_employee,
    "description": DefectSG.desc,
    "severity": DefectSG.severity,
}


class SummaryScene(DefectScene, state=DefectSG.confirm.state):
    """The review: Edit a field, Cancel, or Save; entering it ends any Edit."""

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        return build_summary_text(form), confirm_keyboard(form)

    @on.message.enter()
    async def show_as_message(self, message: Message, state: FSMContext) -> None:
        await drop_keys(state, UD_EDITING)
        await super().show_as_message(message, state)

    @on.callback_query.enter()
    async def show_as_edit(self, callback: CallbackQuery, state: FSMContext) -> None:
        await drop_keys(state, UD_EDITING)
        await super().show_as_edit(callback, state)

    @on.callback_query(EditCB.filter())
    async def edit(
        self, callback: CallbackQuery, callback_data: EditCB, state: FSMContext
    ) -> None:
        """The field's scene draws its own edit prompt and comes back here."""
        await callback.answer()

        # An older summary's button, from before the type moved off a human factor
        defect = await load_defect(state)
        human_factor = defect.defect_type == DefectType.HUMAN_FACTOR
        if callback_data.field == EDIT_RESPONSIBLE and not human_factor:
            return

        field_step = _EDIT_SCENES.get(callback_data.field)
        if field_step is None:
            return

        await state.update_data({UD_EDITING: True})
        await self.wizard.goto(field_step)

    # Split from save so that cancelling never loads the employee
    @on.callback_query(ConfirmCB.filter(~F.confirmed))
    async def decline(self, callback: CallbackQuery) -> None:
        await self.cancel(callback)

    @on.callback_query(ConfirmCB.filter(F.confirmed))
    async def save(
        self,
        callback: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        employee: Employee | None,
    ) -> None:
        await confirm_defect(callback, state, bot, employee)
