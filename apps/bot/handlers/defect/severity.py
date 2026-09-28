from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import SeverityCB
from apps.bot.constants import SEVERITY_LABELS, UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import severity_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

from .scene import DefectScene
from .text import build_description_added_text, build_description_skipped_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen


class SeverityScene(DefectScene, state=DefectSG.severity.state):
    """Judged last, once the evidence is in; the summary comes next, from an Edit too."""

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        return DefectSG.desc

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if data.get(UD_EDITING):
            return str(M.EDIT_SEVERITY), severity_keyboard()
        if form.description:
            return build_description_added_text(), severity_keyboard()
        return build_description_skipped_text(), severity_keyboard()

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

        await self.wizard.goto(DefectSG.confirm)
