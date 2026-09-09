from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_PHOTO_SKIP
from apps.bot.constants import SEVERITY_LABELS, UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

from .summary import show_summary

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import SeverityCB


async def receive_severity(
    callback: CallbackQuery, callback_data: SeverityCB, state: FSMContext
) -> None:
    """Handle incoming severity selection from inline keyboard."""
    await callback.answer()

    sev_value = callback_data.value
    sev_label = str(SEVERITY_LABELS.get(sev_value, sev_value))

    defect = await load_defect(state)
    defect.severity = sev_value
    defect.severity_label = sev_label
    await save_defect(state, defect)

    if (await state.get_data()).get(UD_EDITING):
        await show_summary(callback.message.edit_text, state, defect)
        return

    await callback.message.edit_text(
        str(M.SEVERITY_CONFIRMED).format(label=sev_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(CB_PHOTO_SKIP),
    )
    await state.set_state(DefectSG.photo)
