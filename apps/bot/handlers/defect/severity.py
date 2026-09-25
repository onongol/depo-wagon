from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import SeverityCB
from apps.bot.constants import SEVERITY_LABELS, UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import severity_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

from .scene import DefectScene
from .text import (
    build_defect_type_confirmed_text,
    build_responsible_employee_confirmed_text,
    build_responsible_employee_skipped_text,
)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen


class SeverityScene(DefectScene, state=DefectSG.severity.state):
    """The severity, from buttons; Edit ▸ Severity reopens it.

    A human factor comes here from the employee step, and the screen says how it went.
    """

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if data.get(UD_EDITING):
            return str(M.EDIT_SEVERITY), severity_keyboard()
        if form.defect_type != DefectType.HUMAN_FACTOR:
            text = build_defect_type_confirmed_text(form.defect_type_label)
        elif form.responsible_employee_label:
            text = build_responsible_employee_confirmed_text(
                form.responsible_employee_label
            )
        else:
            text = build_responsible_employee_skipped_text()
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

        await self.go_on(state, DefectSG.photo)
