import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import UD_LAST_PHOTO_MSG, UD_RESP_SEARCH
from apps.bot.fsm import save_employees
from apps.bot.keyboards.defect import measurement_choice_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.user_data import EmployeeRef
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
    await state.set_data(data)

    if defect.defect_type == DefectType.HUMAN_FACTOR:
        try:
            employees = await services.get_employees_by_department(
                defect.department or ""
            )
        except Exception:
            logger.exception("Failed to fetch employees in after_photos")
            await send(str(M.SESSION_ERROR))
            await state.set_state(None)
            return

        # EmployeeRef, not the ORM objects: conversation state is stored as JSON.
        await save_employees(state, [EmployeeRef.from_employee(e) for e in employees])
        await state.update_data({UD_RESP_SEARCH: ""})

        await show_responsible_employee_list(send, state, page=0, edit=True)
        await state.set_state(DefectSG.responsible_employee)
        return

    await send(str(M.ASK_MEASUREMENT), reply_markup=measurement_choice_keyboard())
    await state.set_state(DefectSG.measurement_choice)
