from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import SeverityCB
from apps.bot.constants import SEVERITY_EMOJI, FSMKey
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import severity_keyboard
from apps.bot.states import DefectSG
from apps.bot.utils.choices import emoji_label
from apps.defects.constants import DefectSeverity

from .scene import DefectScene
from .text import build_ask_severity_text, build_edit_severity_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen


class SeverityScene(DefectScene, state=DefectSG.severity.state):
    """Judged once the evidence is in; the verdict is asked next."""

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        return DefectSG.desc

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if data.get(FSMKey.EDITING):
            return build_edit_severity_text(), severity_keyboard()
        return build_ask_severity_text(), severity_keyboard()

    @on.callback_query(SeverityCB.filter())
    async def receive(
        self, callback: CallbackQuery, callback_data: SeverityCB, state: FSMContext
    ) -> None:
        await callback.answer()

        sev_value = callback_data.value
        sev_label = emoji_label(SEVERITY_EMOJI, DefectSeverity, sev_value)

        defect = await load_defect(state)
        defect.severity = sev_value
        defect.severity_label = sev_label
        await save_defect(state, defect)

        await self.go_on(state, DefectSG.employee_verdict)
