from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_DESC_SKIP
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.scene import ScenesManager
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import EditCB


# Scenes draw their own edit prompt on entering
_EDIT_SCENES = {
    "wagon": DefectSG.wagon_num,
    "node": DefectSG.node,
    "part_number": DefectSG.part_number,
    "defect_type": DefectSG.defect_type,
    "severity": DefectSG.severity,
}

# field -> (prompt, keyboard built from the defect under edit, state to enter).
# Keyboards are built per call: their callback payloads are per-message.
_EDIT_STEPS = {
    "description": (
        M.EDIT_DESCRIPTION,
        lambda _: skip_keyboard(CB_DESC_SKIP),
        DefectSG.desc,
    ),
}


async def start_edit(
    callback: CallbackQuery,
    callback_data: EditCB,
    state: FSMContext,
    scenes: ScenesManager,
) -> None:
    """Render the chosen field's input and route to its state in edit mode."""
    await callback.answer()

    if scene := _EDIT_SCENES.get(callback_data.field):
        await state.update_data({UD_EDITING: True})
        await scenes.enter(scene)
        return

    defect = await load_defect(state)

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
