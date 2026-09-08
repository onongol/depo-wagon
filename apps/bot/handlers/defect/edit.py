from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_DESC_SKIP, CB_PART_NUMBER_SKIP
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import (
    defect_type_keyboard,
    node_keyboard_for_department,
    severity_keyboard,
)
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import EditCB


# field -> (prompt, keyboard built from the defect under edit, state to enter).
# Keyboards are built per call: their callback payloads are per-message.
_EDIT_STEPS = {
    "wagon": (M.EDIT_WAGON, None, DefectSG.wagon_num),
    "node": (
        M.EDIT_NODE,
        lambda defect: node_keyboard_for_department(defect.department or ""),
        DefectSG.node,
    ),
    "part_number": (
        M.EDIT_PART_NUMBER,
        lambda _: skip_keyboard(CB_PART_NUMBER_SKIP),
        DefectSG.part_number,
    ),
    "defect_type": (
        M.EDIT_DEFECT_TYPE,
        lambda _: defect_type_keyboard(),
        DefectSG.defect_type,
    ),
    "severity": (M.EDIT_SEVERITY, lambda _: severity_keyboard(), DefectSG.severity),
    "description": (
        M.EDIT_DESCRIPTION,
        lambda _: skip_keyboard(CB_DESC_SKIP),
        DefectSG.desc,
    ),
}


async def start_edit(
    callback: CallbackQuery, callback_data: EditCB, state: FSMContext
) -> None:
    """Render the chosen field's input and route to its state in edit mode."""
    await callback.answer()

    defect = await load_defect(state)
    if defect is None:
        await callback.message.edit_text(str(M.DEFECT_CANCELLED))
        await state.set_state(None)
        return

    step = _EDIT_STEPS.get(callback_data.field)
    if step is None:
        await state.set_state(DefectSG.confirm)
        return

    await state.update_data({UD_EDITING: True})

    prompt, keyboard, target = step
    await callback.message.edit_text(
        str(prompt),
        parse_mode=M.PARSE_MODE,
        reply_markup=keyboard(defect) if keyboard else None,
    )
    await state.set_state(target)
