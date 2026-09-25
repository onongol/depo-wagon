"""Each plain step's screen, rebuilt from the form so Continue can show it again.

A step that is a Scene draws its own; the table shrinks as steps move.
"""

import html
from typing import TYPE_CHECKING

from apps.bot.callback_data import (
    CB_DESC_SKIP,
    CB_NORM_SKIP,
    CB_PART_NUMBER_SKIP,
    CB_PHOTO_SKIP,
    CB_UNIT_SKIP,
)
from apps.bot.fsm import load_defect
from apps.bot.keyboards.common import done_keyboard, skip_keyboard
from apps.bot.keyboards.confirm import employee_verdict_keyboard
from apps.bot.keyboards.defect import (
    defect_type_keyboard,
    department_keyboard,
    node_keyboard_for_department,
    severity_keyboard,
)
from apps.bot.keyboards.measurement import (
    dimension_keyboard,
    measurement_choice_keyboard,
    measurement_next_keyboard,
)
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

from .responsible_employee import show_responsible_employee_list
from .scene import as_send_kwargs
from .scenes import scene_for
from .summary import show_summary
from .text import build_wagon_confirmed_text

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext
    from aiogram.types import InlineKeyboardMarkup

    from apps.bot.user_data import DefectData


def _defect_type(defect: DefectData) -> tuple[str, InlineKeyboardMarkup]:
    if defect.part_number:
        part_number = html.escape(defect.part_number)
        text = str(M.PART_NUMBER_CONFIRMED).format(part_number=part_number)
    else:
        text = str(M.PART_NUMBER_SKIPPED)
    return text, defect_type_keyboard()


def _photo(defect: DefectData) -> tuple[str, InlineKeyboardMarkup]:
    if defect.photos:
        text = str(M.PHOTO_RECEIVED).format(count=len(defect.photos))
        return text, done_keyboard(CB_PHOTO_SKIP)
    text = str(M.SEVERITY_CONFIRMED).format(label=defect.severity_label)
    return text, skip_keyboard(CB_PHOTO_SKIP)


# As each step first showed it; confirm and responsible_employee render async
_SCREENS = {
    DefectSG.department.state: lambda d: (
        build_wagon_confirmed_text(d.wagon_number),
        department_keyboard(),
    ),
    DefectSG.node.state: lambda d: (
        str(M.DEPARTMENT_CONFIRMED).format(label=d.department_label),
        node_keyboard_for_department(d.department or ""),
    ),
    DefectSG.part_number.state: lambda _: (
        str(M.PART_NUMBER_PROMPT),
        skip_keyboard(CB_PART_NUMBER_SKIP),
    ),
    DefectSG.defect_type.state: _defect_type,
    DefectSG.severity.state: lambda d: (
        str(M.DEFECT_TYPE_CONFIRMED).format(label=d.defect_type_label),
        severity_keyboard(),
    ),
    DefectSG.photo.state: _photo,
    DefectSG.measurement_choice.state: lambda d: (
        str(M.ASK_MEASUREMENT),
        measurement_next_keyboard()
        if d.measurements
        else measurement_choice_keyboard(),
    ),
    DefectSG.measurement_dimension.state: lambda _: (
        str(M.ASK_DIMENSION),
        dimension_keyboard(),
    ),
    DefectSG.measurement_value.state: lambda d: (
        str(M.DIMENSION_CONFIRMED).format(label=d.current_measurement.dimension_label),
        None,
    ),
    DefectSG.measurement_norm.state: lambda _: (
        str(M.ASK_NORM),
        skip_keyboard(CB_NORM_SKIP),
    ),
    DefectSG.measurement_unit.state: lambda _: (
        str(M.ASK_UNIT),
        skip_keyboard(CB_UNIT_SKIP),
    ),
    DefectSG.desc.state: lambda _: (
        str(M.ASK_DESCRIPTION),
        skip_keyboard(CB_DESC_SKIP),
    ),
    DefectSG.employee_verdict.state: lambda _: (
        str(M.ASK_EMPLOYEE_VERDICT),
        employee_verdict_keyboard(),
    ),
}


async def show_current_step(send: Callable[..., Awaitable], state: FSMContext) -> bool:
    """False for saving, the one step with no screen of its own."""
    step = await state.get_state()
    defect = await load_defect(state)

    if scene := scene_for(step):
        content, keyboard = await scene.screen(defect, await state.get_data())
        await send(**as_send_kwargs(content), reply_markup=keyboard)
    elif step == DefectSG.confirm.state:
        await show_summary(send, state, defect)
    elif step == DefectSG.responsible_employee.state:
        await show_responsible_employee_list(send, state, defect.department)
    elif screen := _SCREENS.get(step):
        content, keyboard = screen(defect)
        await send(**as_send_kwargs(content), reply_markup=keyboard)
    else:
        return False

    return True
