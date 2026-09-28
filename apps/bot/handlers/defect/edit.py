from typing import TYPE_CHECKING

from apps.bot.constants import EDIT_RESPONSIBLE, UD_EDITING
from apps.bot.fsm import load_defect
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

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
    EDIT_RESPONSIBLE: DefectSG.responsible_employee,
    "severity": DefectSG.severity,
    "description": DefectSG.desc,
}


async def start_edit(
    callback: CallbackQuery,
    callback_data: EditCB,
    state: FSMContext,
    scenes: ScenesManager,
) -> None:
    """Enter the chosen field's scene in edit mode."""
    await callback.answer()

    defect = await load_defect(state)

    # An older summary's button, from before the type moved off a human factor
    human_factor = defect.defect_type == DefectType.HUMAN_FACTOR
    if callback_data.field == EDIT_RESPONSIBLE and not human_factor:
        return

    scene = _EDIT_SCENES.get(callback_data.field)
    if scene is None:
        await state.set_state(DefectSG.confirm)
        return

    await state.update_data({UD_EDITING: True})
    await scenes.enter(scene)
