from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot import services
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.states import DefectSG

from .scene import STEP_TEXT, DefectScene
from .text import (
    build_edit_wagon_text,
    build_new_defect_text,
    build_wagon_not_found_text,
)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

    from apps.bot.user_data import DefectData

    from .scene import Screen


class WagonScene(DefectScene, state=DefectSG.wagon_num.state):
    """The first step, and the one Edit ▸ Wagon reopens from the summary."""

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if data.get(UD_EDITING):
            return build_edit_wagon_text(), None
        return build_new_defect_text(), None

    @on.message(*STEP_TEXT)
    async def receive(self, message: Message, state: FSMContext) -> None:
        """Look up the typed wagon number."""
        number = message.text.strip()
        wagon = await services.get_wagon_by_number(number)
        if not wagon:
            await message.answer(**build_wagon_not_found_text(number).as_kwargs())
            return

        defect = await load_defect(state)
        defect.wagon_id = wagon.id
        defect.wagon_number = wagon.number
        await save_defect(state, defect)

        await self.go_on(state, DefectSG.department)
