from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import CB_PHOTO_SKIP, SeverityCB
from apps.bot.constants import SEVERITY_LABELS, UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import severity_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

from .scene import DefectScene
from .text import build_defect_type_confirmed_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen


class SeverityScene(DefectScene, state=DefectSG.severity.state):
    """The severity, from buttons; Edit ▸ Severity reopens it."""

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if data.get(UD_EDITING):
            return str(M.EDIT_SEVERITY), severity_keyboard()
        text = build_defect_type_confirmed_text(form.defect_type_label)
        return text, severity_keyboard()

    @on.callback_query(SeverityCB.filter())
    async def receive(
        self, callback: CallbackQuery, callback_data: SeverityCB, state: FSMContext
    ) -> None:
        await callback.answer()

        sev_value = callback_data.value
        sev_label = str(SEVERITY_LABELS.get(sev_value, sev_value))

        defect = await load_defect(state)
        defect.severity = sev_value
        defect.severity_label = sev_label
        await save_defect(state, defect)

        if await self.back_to_summary_if_editing(state):
            return

        await callback.message.edit_text(
            str(M.SEVERITY_CONFIRMED).format(label=sev_label),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard(CB_PHOTO_SKIP),
        )
        await state.set_state(DefectSG.photo)
