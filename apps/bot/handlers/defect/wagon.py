from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot import services
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import department_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

from .scene import STEP_TEXT, DefectScene
from .summary import show_summary
from .text import (
    build_new_defect_text,
    build_wagon_confirmed_text,
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
            return str(M.EDIT_WAGON), None
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

        if (await state.get_data()).get(UD_EDITING):
            await show_summary(message.answer, state, defect)
            return

        await message.answer(
            **build_wagon_confirmed_text(wagon.number).as_kwargs(),
            reply_markup=department_keyboard(),
        )
        await state.set_state(DefectSG.department)
