from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_DESC_SKIP
from apps.bot.constants import UD_LAST_MEDIA_GROUP, UD_LAST_PHOTO_MSG
from apps.bot.fsm import drop_keys
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.scene import SceneWizard

    from apps.bot.user_data import DefectData


async def after_photos(
    wizard: SceneWizard,
    send: Callable[..., Awaitable],
    defect: DefectData,
    state: FSMContext,
) -> None:
    """A human factor has no measurements: straight on to the description."""
    await drop_keys(state, UD_LAST_PHOTO_MSG, UD_LAST_MEDIA_GROUP)

    if defect.defect_type == DefectType.HUMAN_FACTOR:
        await send(
            str(M.ASK_DESCRIPTION),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard(CB_DESC_SKIP),
        )
        await state.set_state(DefectSG.desc)
        return

    await wizard.goto(DefectSG.measurement_choice)
