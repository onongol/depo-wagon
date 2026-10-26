from typing import TYPE_CHECKING

from apps.bot.constants import FSMKey
from apps.bot.fsm import drop_keys
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext

    from apps.bot.handlers.defect.scene import DefectScene
    from apps.bot.user_data import DefectData


async def after_photos(
    scene: DefectScene, defect: DefectData, state: FSMContext
) -> None:
    """A human factor has no measurements: straight on to the description."""
    await drop_keys(state, FSMKey.LAST_MEDIA_GROUP)

    if defect.defect_type == DefectType.HUMAN_FACTOR:
        await scene.go_on(state, DefectSG.desc)
    else:
        await scene.go_on(state, DefectSG.measurement_choice)
