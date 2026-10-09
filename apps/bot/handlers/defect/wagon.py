from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot import services
from apps.bot.constants import FSMKey
from apps.bot.fsm import load_defect, save_defect
from apps.bot.states import DefectSG
from apps.bot.utils.screens import delete_input

from .scene import STEP_TEXT, DefectScene
from .text import (
    build_ask_wagon_text,
    build_edit_wagon_text,
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
        if data.get(FSMKey.EDITING):
            return build_edit_wagon_text(), None
        return build_ask_wagon_text(), None

    @on.message(*STEP_TEXT)
    async def receive(self, message: Message, state: FSMContext) -> None:
        """Look up the typed wagon number."""
        number = message.text.strip()
        await delete_input(message)
        wagon = await services.get_wagon_by_number(number)
        if not wagon:
            notice = build_wagon_not_found_text(number)
            await self.show_as_message(message, state, notice=notice)
            return

        defect = await load_defect(state)
        defect.wagon_id = wagon.id
        defect.wagon_number = wagon.number
        await save_defect(state, defect)

        await self.go_on(state, DefectSG.department)
