from typing import TYPE_CHECKING

from apps.bot.constants import UD_LAST_MEDIA_GROUP, UD_LAST_PHOTO_MSG
from apps.bot.fsm import drop_keys
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.scene import SceneWizard

    from apps.bot.user_data import DefectData


async def after_photos(
    wizard: SceneWizard, defect: DefectData, state: FSMContext
) -> None:
    """A human factor has no measurements: straight on to the description."""
    await drop_keys(state, UD_LAST_PHOTO_MSG, UD_LAST_MEDIA_GROUP)

    if defect.defect_type == DefectType.HUMAN_FACTOR:
        await wizard.goto(DefectSG.desc)
    else:
        await wizard.goto(DefectSG.measurement_choice)
