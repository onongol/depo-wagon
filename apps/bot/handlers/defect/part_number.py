from typing import TYPE_CHECKING, Any

from aiogram import F
from aiogram.fsm.scene import on

from apps.bot.callback_data import CB_PART_NUMBER_SKIP
from apps.bot.constants import FSMKey
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.states import DefectSG
from apps.bot.utils.screens import delete_input

from .scene import STEP_TEXT, DefectScene
from .text import (
    build_ask_part_number_text,
    build_edit_part_number_text,
    build_part_number_too_long_text,
)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery, Message

    from apps.bot.user_data import DefectData

    from .scene import Screen

PART_NUMBER_MAX_LENGTH = 100


class PartNumberScene(DefectScene, state=DefectSG.part_number.state):
    """Typed or skipped; from the next step on, a skipped one shows as a dash."""

    async def _record(self, state: FSMContext, part_number: str) -> None:
        defect = await load_defect(state)
        defect.part_number = part_number
        await save_defect(state, defect)
        await self.go_on(state, DefectSG.defect_type)

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        return DefectSG.node

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        keyboard = skip_keyboard(CB_PART_NUMBER_SKIP)
        if data.get(FSMKey.EDITING):
            return build_edit_part_number_text(), keyboard
        return build_ask_part_number_text(), keyboard

    @on.message(*STEP_TEXT)
    async def receive(self, message: Message, state: FSMContext) -> None:
        part_number = message.text.strip()
        if len(part_number) > PART_NUMBER_MAX_LENGTH:
            too_long = build_part_number_too_long_text(
                len(part_number), PART_NUMBER_MAX_LENGTH
            )
            # Left in the chat to be copied and shortened
            await self.show_as_message(message, state, notice=too_long, below=True)
            return

        await delete_input(message)
        await self._record(state, part_number)

    @on.callback_query(F.data == CB_PART_NUMBER_SKIP)
    async def skip(self, callback: CallbackQuery, state: FSMContext) -> None:
        """A skip is an empty part number, which also clears one an Edit reopened."""
        await callback.answer()
        await self._record(state, "")
