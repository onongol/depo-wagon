"""Routers for defect registration.

Disjoint by state: the entry answers only outside DefectSG, and inside it the
flow asks whether to continue or start over, so a running form is never wiped
without the user choosing to.
"""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter

from apps.bot.callback_data import (
    CB_CANCEL,
    CB_DEFECT_CONTINUE,
    CB_DEFECT_RESTART,
    CB_DESC_SKIP,
    CB_MEAS_ADD,
    CB_MEAS_DONE,
    CB_MEAS_SKIP,
    CB_NORM_SKIP,
    CB_PART_NUMBER_SKIP,
    CB_PHOTO_SKIP,
    CB_RESP_EMP_SKIP,
    CB_UNIT_SKIP,
    ConfirmCB,
    DefectTypeCB,
    DepartmentCB,
    DimensionCB,
    EditCB,
    NodeCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    SeverityCB,
    VerdictCB,
)
from apps.bot.constants import BTN_NEW_DEFECT
from apps.bot.filters import NotACommand
from apps.bot.keyboards.menu import MENU_TEXTS
from apps.bot.middlewares import DefectFormMiddleware
from apps.bot.states import DefectSG

from .cancel import cancel_defect_button, stale_callback
from .confirm import confirm_defect
from .defect_type import receive_defect_type
from .department import receive_department
from .description import receive_description, skip_description
from .edit import start_edit
from .measurement import (
    measurement_add,
    measurement_done,
    receive_dimension,
    receive_measurement_value,
    receive_norm_value,
    receive_unit,
    skip_norm_value,
    skip_unit,
)
from .node import receive_node
from .part_number import receive_part_number, skip_part_number
from .photo import receive_photo, skip_photo
from .responsible_employee import (
    page_responsible_employee,
    search_responsible_employee,
    select_responsible_employee,
    skip_responsible_employee,
)
from .restart import (
    continue_defect,
    defect_in_progress,
    menu_button_mid_flow,
    restart_defect,
)
from .severity import receive_severity
from .start import new_defect_start
from .verdict import receive_employee_verdict
from .wagon import receive_wagon_number

_TEXT = (F.text, NotACommand())


def get_defect_flow_router() -> Router:
    """Every step, filtered by the state it belongs to."""
    router = Router(name="defect_flow")
    msg = router.message.register
    cb = router.callback_query.register

    # Outer, so no step is reached with a form that is stale or gone
    router.message.outer_middleware(DefectFormMiddleware())
    router.callback_query.outer_middleware(DefectFormMiddleware())

    # Menu buttons ahead of every step; a text step would take one for an answer
    running = StateFilter(DefectSG)
    msg(defect_in_progress, running, Command("new_defect"))
    msg(defect_in_progress, running, F.text == str(BTN_NEW_DEFECT))
    msg(menu_button_mid_flow, running, F.text.in_(MENU_TEXTS))
    msg(
        menu_button_mid_flow,
        running,
        Command("start", "my_tasks", "ask", "support", "help"),
    )
    cb(continue_defect, running, F.data == CB_DEFECT_CONTINUE)
    cb(restart_defect, running, F.data == CB_DEFECT_RESTART)

    msg(receive_wagon_number, StateFilter(DefectSG.wagon_num), *_TEXT)
    cb(receive_department, StateFilter(DefectSG.department), DepartmentCB.filter())
    cb(receive_node, StateFilter(DefectSG.node), NodeCB.filter())

    msg(receive_part_number, StateFilter(DefectSG.part_number), *_TEXT)
    cb(
        skip_part_number,
        StateFilter(DefectSG.part_number),
        F.data == CB_PART_NUMBER_SKIP,
    )

    cb(receive_defect_type, StateFilter(DefectSG.defect_type), DefectTypeCB.filter())
    cb(receive_severity, StateFilter(DefectSG.severity), SeverityCB.filter())

    msg(receive_photo, StateFilter(DefectSG.photo), F.photo)
    cb(skip_photo, StateFilter(DefectSG.photo), F.data == CB_PHOTO_SKIP)

    resp = StateFilter(DefectSG.responsible_employee)
    cb(select_responsible_employee, resp, ResponsibleEmployeeCB.filter())
    cb(skip_responsible_employee, resp, F.data == CB_RESP_EMP_SKIP)
    cb(page_responsible_employee, resp, ResponsibleEmployeePageCB.filter())
    msg(search_responsible_employee, resp, *_TEXT)

    choice = StateFilter(DefectSG.measurement_choice)
    cb(measurement_add, choice, F.data == CB_MEAS_ADD)
    cb(measurement_done, choice, F.data.in_({CB_MEAS_SKIP, CB_MEAS_DONE}))

    cb(
        receive_dimension,
        StateFilter(DefectSG.measurement_dimension),
        DimensionCB.filter(),
    )
    msg(receive_measurement_value, StateFilter(DefectSG.measurement_value), *_TEXT)

    norm = StateFilter(DefectSG.measurement_norm)
    msg(receive_norm_value, norm, *_TEXT)
    cb(skip_norm_value, norm, F.data == CB_NORM_SKIP)

    unit = StateFilter(DefectSG.measurement_unit)
    msg(receive_unit, unit, *_TEXT)
    cb(skip_unit, unit, F.data == CB_UNIT_SKIP)

    msg(receive_description, StateFilter(DefectSG.desc), *_TEXT)
    cb(skip_description, StateFilter(DefectSG.desc), F.data == CB_DESC_SKIP)

    cb(start_edit, StateFilter(DefectSG.confirm), EditCB.filter())
    # Split so that cancelling never loads the employee
    cb(
        cancel_defect_button,
        StateFilter(DefectSG.confirm),
        ConfirmCB.filter(~F.confirmed),
    )
    cb(confirm_defect, StateFilter(DefectSG.confirm), ConfirmCB.filter(F.confirmed))

    cb(
        receive_employee_verdict,
        StateFilter(DefectSG.employee_verdict),
        VerdictCB.filter(),
    )

    # Fallbacks: the Cancel button, then any other tap. /cancel is the global router's.
    cb(cancel_defect_button, StateFilter(DefectSG), F.data == CB_CANCEL)
    cb(stale_callback, StateFilter(DefectSG))

    return router


def get_defect_entry_router() -> Router:
    """The two ways in, outside a running form."""
    router = Router(name="defect_entry")
    router.message.filter(~StateFilter(DefectSG))
    router.message.register(new_defect_start, Command("new_defect"))
    router.message.register(new_defect_start, F.text == str(BTN_NEW_DEFECT))
    return router
