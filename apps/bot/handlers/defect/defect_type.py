from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import DefectTypeCB
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import defect_type_keyboard, severity_keyboard
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

from .scene import DefectScene
from .text import (
    build_defect_type_confirmed_text,
    build_edit_defect_type_text,
    build_part_number_confirmed_text,
    build_part_number_skipped_text,
)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen

_DEFECT_TYPE_LABELS = dict(DefectType.choices)


class DefectTypeScene(DefectScene, state=DefectSG.defect_type.state):
    """The defect type, from buttons; the screen first says how the part number went."""

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        keyboard = defect_type_keyboard()
        if data.get(UD_EDITING):
            return build_edit_defect_type_text(), keyboard
        if form.part_number:
            return build_part_number_confirmed_text(form.part_number), keyboard
        return build_part_number_skipped_text(), keyboard

    @on.callback_query(DefectTypeCB.filter())
    async def receive(
        self, callback: CallbackQuery, callback_data: DefectTypeCB, state: FSMContext
    ) -> None:
        await callback.answer()

        dtype_value = callback_data.value
        dtype_label = str(_DEFECT_TYPE_LABELS.get(dtype_value, dtype_value))

        defect = await load_defect(state)
        defect.defect_type = dtype_value
        defect.defect_type_label = dtype_label
        await save_defect(state, defect)

        if await self.back_to_summary_if_editing(state):
            return

        await callback.message.edit_text(
            **build_defect_type_confirmed_text(dtype_label).as_kwargs(),
            reply_markup=severity_keyboard(),
        )
        await state.set_state(DefectSG.severity)
