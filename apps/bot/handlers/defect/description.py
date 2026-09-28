from typing import TYPE_CHECKING, Any

from aiogram import F
from aiogram.fsm.scene import on

from apps.bot.callback_data import CB_DESC_SKIP
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.states import DefectSG

from .scene import STEP_TEXT, DefectScene
from .summary import show_summary
from .text import (
    build_ask_description_text,
    build_description_too_long_text,
    build_edit_description_text,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

    from apps.bot.user_data import DefectData

    from .scene import Screen

_MAX_DESCRIPTION_LEN = 1000


class DescriptionScene(DefectScene, state=DefectSG.desc.state):
    """Typed or skipped, the summary comes next, from an Edit as well."""

    async def _record(
        self, send: Callable[..., Awaitable], state: FSMContext, description: str
    ) -> None:
        defect = await load_defect(state)
        defect.description = description
        await save_defect(state, defect)
        await show_summary(send, state, defect)

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if data.get(UD_EDITING):
            return build_edit_description_text(), skip_keyboard(CB_DESC_SKIP)
        return build_ask_description_text(), skip_keyboard(CB_DESC_SKIP)

    @on.message(*STEP_TEXT)
    async def receive(self, message: Message, state: FSMContext) -> None:
        text = message.text.strip()
        if len(text) > _MAX_DESCRIPTION_LEN:
            too_long = build_description_too_long_text(len(text), _MAX_DESCRIPTION_LEN)
            await message.answer(**too_long.as_kwargs())
            return

        await self._record(message.answer, state, text)

    @on.callback_query(F.data == CB_DESC_SKIP)
    async def skip(self, callback: CallbackQuery, state: FSMContext) -> None:
        """A skip is an empty description, which also clears one an Edit reopened."""
        await callback.answer()
        await self._record(callback.message.edit_text, state, "")
