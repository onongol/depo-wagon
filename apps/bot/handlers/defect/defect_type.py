from typing import TYPE_CHECKING

from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import severity_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

from .summary import show_summary

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import DefectTypeCB

_DEFECT_TYPE_LABELS = dict(DefectType.choices)


async def receive_defect_type(
    callback: CallbackQuery, callback_data: DefectTypeCB, state: FSMContext
) -> None:
    """Handle incoming defect type selection from inline keyboard."""
    await callback.answer()

    dtype_value = callback_data.value
    dtype_label = str(_DEFECT_TYPE_LABELS.get(dtype_value, dtype_value))

    defect = await load_defect(state)
    defect.defect_type = dtype_value
    defect.defect_type_label = dtype_label
    await save_defect(state, defect)

    if (await state.get_data()).get(UD_EDITING):
        await show_summary(callback.message.edit_text, state, defect)
        return

    await callback.message.edit_text(
        str(M.DEFECT_TYPE_CONFIRMED).format(label=dtype_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=severity_keyboard(),
    )
    await state.set_state(DefectSG.severity)
