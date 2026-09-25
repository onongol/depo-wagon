from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_DESC_SKIP
from apps.bot.constants import UD_LAST_MEDIA_GROUP, UD_LAST_PHOTO_MSG
from apps.bot.handlers.defect.text import build_ask_measurement_text
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.measurement import measurement_choice_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext

    from apps.bot.user_data import DefectData


async def after_photos(
    send: Callable[..., Awaitable], defect: DefectData, state: FSMContext
) -> None:
    """A human factor has no measurements: straight on to the description."""
    data = await state.get_data()
    data.pop(UD_LAST_PHOTO_MSG, None)
    data.pop(UD_LAST_MEDIA_GROUP, None)
    await state.set_data(data)

    if defect.defect_type == DefectType.HUMAN_FACTOR:
        await send(
            str(M.ASK_DESCRIPTION),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard(CB_DESC_SKIP),
        )
        await state.set_state(DefectSG.desc)
        return

    await send(
        **build_ask_measurement_text().as_kwargs(),
        reply_markup=measurement_choice_keyboard(),
    )
    await state.set_state(DefectSG.measurement_choice)
