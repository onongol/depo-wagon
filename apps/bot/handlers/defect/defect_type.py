import html
from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import DefectTypeCB
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import defect_type_keyboard, severity_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

from .scene import DefectScene

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
            return str(M.EDIT_DEFECT_TYPE), keyboard
        if form.part_number:
            part_number = html.escape(form.part_number)
            text = str(M.PART_NUMBER_CONFIRMED).format(part_number=part_number)
            return text, keyboard
        return str(M.PART_NUMBER_SKIPPED), keyboard

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
            str(M.DEFECT_TYPE_CONFIRMED).format(label=dtype_label),
            parse_mode=M.PARSE_MODE,
            reply_markup=severity_keyboard(),
        )
        await state.set_state(DefectSG.severity)
