from typing import TYPE_CHECKING

from apps.bot.fsm import load_defect, save_defect
from apps.bot.messages import BotMessages as M

from .summary import show_summary

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

_MAX_DESCRIPTION_LEN = 1000


async def receive_description(message: Message, state: FSMContext) -> None:
    """Handle incoming description text."""
    defect = await load_defect(state)
    if defect is None:
        await message.answer(str(M.DEFECT_CANCELLED))
        await state.set_state(None)
        return

    text = message.text.strip()
    if len(text) > _MAX_DESCRIPTION_LEN:
        await message.answer(
            str(M.DESCRIPTION_TOO_LONG).format(
                length=len(text), max=_MAX_DESCRIPTION_LEN
            ),
            parse_mode=M.PARSE_MODE,
        )
        return

    defect.description = text
    await save_defect(state, defect)
    await show_summary(message.answer, state, defect)


async def skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle description skip — set empty description and show summary."""
    await callback.answer()

    defect = await load_defect(state)
    if defect is None:
        await callback.message.edit_text(str(M.DEFECT_CANCELLED))
        await state.set_state(None)
        return

    defect.description = ""
    await save_defect(state, defect)
    await show_summary(callback.message.edit_text, state, defect)
