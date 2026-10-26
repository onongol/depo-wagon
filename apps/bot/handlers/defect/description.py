from typing import TYPE_CHECKING, Any

from aiogram import F
from aiogram.fsm.scene import on

from apps.bot.callback_data import CB_DESC_SKIP
from apps.bot.constants import FSMKey
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.states import DefectSG
from apps.bot.utils.screens import delete_input
from apps.defects.constants import DefectType

from .scene import STEP_TEXT, DefectScene
from .text import (
    build_ask_description_text,
    build_description_too_long_text,
    build_edit_description_text,
)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery, Message

    from apps.bot.user_data import DefectData

    from .scene import Screen

_MAX_DESCRIPTION_LEN = 1000


class DescriptionScene(DefectScene, state=DefectSG.desc.state):
    """Typed or skipped; from the next step on, a skipped one shows as a dash."""

    async def _record(self, state: FSMContext, description: str) -> None:
        defect = await load_defect(state)
        defect.description = description
        await save_defect(state, defect)
        await self.go_on(state, DefectSG.severity)

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        """A human factor has no measurements."""
        if form.defect_type == DefectType.HUMAN_FACTOR:
            return DefectSG.photo
        return DefectSG.measurement_choice

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if data.get(FSMKey.EDITING):
            return build_edit_description_text(), skip_keyboard(CB_DESC_SKIP)
        return build_ask_description_text(), skip_keyboard(CB_DESC_SKIP)

    @on.message(*STEP_TEXT)
    async def receive(self, message: Message, state: FSMContext) -> None:
        text = message.text.strip()
        if len(text) > _MAX_DESCRIPTION_LEN:
            too_long = build_description_too_long_text(len(text), _MAX_DESCRIPTION_LEN)
            # Left in the chat to be copied and shortened
            await self.show_as_message(message, state, notice=too_long, below=True)
            return

        await delete_input(message)
        await self._record(state, text)

    @on.callback_query(F.data == CB_DESC_SKIP)
    async def skip(self, callback: CallbackQuery, state: FSMContext) -> None:
        """A skip is an empty description, which also clears one an Edit reopened."""
        await callback.answer()
        await self._record(state, "")
