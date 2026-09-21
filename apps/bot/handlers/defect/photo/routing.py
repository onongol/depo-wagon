import logging
from typing import TYPE_CHECKING

from apps.bot.constants import UD_LAST_MEDIA_GROUP, UD_LAST_PHOTO_MSG, UD_RESP_SEARCH
from apps.bot.keyboards.measurement import measurement_choice_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.defects.constants import DefectType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext

    from apps.bot.user_data import DefectData

logger = logging.getLogger(__name__)


async def after_photos(
    send: Callable[..., Awaitable], defect: DefectData, state: FSMContext
) -> None:
    """Route to responsible_employee or measurement depending on defect type."""
    from apps.bot.handlers.defect.responsible_employee import (
        show_responsible_employee_list,
    )

    data = await state.get_data()
    data.pop(UD_LAST_PHOTO_MSG, None)
    data.pop(UD_LAST_MEDIA_GROUP, None)
    await state.set_data(data)

    if defect.defect_type == DefectType.HUMAN_FACTOR:
        await state.update_data({UD_RESP_SEARCH: ""})

        try:
            await show_responsible_employee_list(send, state, defect.department, page=0)
        except Exception:
            logger.exception("Failed to show the employee list in after_photos")
            await send(str(M.SESSION_ERROR))
            await state.set_state(None)
            return

        await state.set_state(DefectSG.responsible_employee)
        return

    await send(str(M.ASK_MEASUREMENT), reply_markup=measurement_choice_keyboard())
    await state.set_state(DefectSG.measurement_choice)
