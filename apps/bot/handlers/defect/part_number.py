import html
from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_PART_NUMBER_SKIP
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import defect_type_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

from .summary import show_summary

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

PART_NUMBER_MAX_LENGTH = 100


async def receive_part_number(message: Message, state: FSMContext) -> None:
    """Handle part number text input."""
    defect = await load_defect(state)
    if defect is None:
        await message.answer(str(M.DEFECT_CANCELLED))
        await state.set_state(None)
        return

    part_number = message.text.strip()
    if len(part_number) > PART_NUMBER_MAX_LENGTH:
        await message.answer(
            str(M.PART_NUMBER_TOO_LONG).format(
                length=len(part_number), max=PART_NUMBER_MAX_LENGTH
            ),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard(CB_PART_NUMBER_SKIP),
        )
        return

    defect.part_number = part_number
    await save_defect(state, defect)

    if (await state.get_data()).get(UD_EDITING):
        await show_summary(message.answer, state, defect)
        return

    await message.answer(
        str(M.PART_NUMBER_CONFIRMED).format(
            part_number=html.escape(defect.part_number)
        ),
        parse_mode=M.PARSE_MODE,
        reply_markup=defect_type_keyboard(),
    )
    await state.set_state(DefectSG.defect_type)


async def skip_part_number(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle part number skip."""
    await callback.answer()

    defect = await load_defect(state)
    if defect is None:
        await callback.message.edit_text(str(M.DEFECT_CANCELLED))
        await state.set_state(None)
        return

    defect.part_number = ""
    await save_defect(state, defect)

    if (await state.get_data()).get(UD_EDITING):
        await show_summary(callback.message.edit_text, state, defect)
        return

    await callback.message.edit_text(
        str(M.PART_NUMBER_SKIPPED),
        parse_mode=M.PARSE_MODE,
        reply_markup=defect_type_keyboard(),
    )
    await state.set_state(DefectSG.defect_type)
