from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import VerdictCB
from apps.bot.constants import VERDICT_EMOJI, FSMKey
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.confirm import employee_verdict_keyboard
from apps.bot.states import DefectSG
from apps.bot.utils.choices import emoji_label
from apps.defects.constants import DefectVerdict

from .scene import DefectScene
from .text import build_ask_verdict_text, build_edit_verdict_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen


class VerdictScene(DefectScene, state=DefectSG.employee_verdict.state):
    """Asked before the save, so the AI's verdict cannot sway it."""

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        return DefectSG.severity

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if data.get(FSMKey.EDITING):
            return build_edit_verdict_text(), employee_verdict_keyboard()
        return build_ask_verdict_text(), employee_verdict_keyboard()

    @on.callback_query(VerdictCB.filter())
    async def receive(
        self, callback: CallbackQuery, callback_data: VerdictCB, state: FSMContext
    ) -> None:
        await callback.answer()

        value = callback_data.value

        defect = await load_defect(state)
        defect.verdict = value
        defect.verdict_label = emoji_label(VERDICT_EMOJI, DefectVerdict, value)
        await save_defect(state, defect)

        await self.wizard.goto(DefectSG.confirm)
