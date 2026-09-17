"""Routers for defect registration.

Split in two on purpose. The flow router is state-filtered and is included
before the entry router, which is how PTB stopped an entry point from
restarting a conversation already in progress: BTN_NEW_DEFECT typed during the
flow reaches receive_wagon_number, whose MENU_TEXTS guard re-prompts, rather
than wiping the form and starting over.
"""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter

from apps.bot.callback_data import (
    CB_CANCEL,
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
from apps.bot.middlewares import StaleSchemaMiddleware
from apps.bot.states import DefectSG

from .cancel import cancel_defect_button, cancel_defect_command, stale_callback
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

    # Outer, so a form from an older schema never reaches a step that would
    # dereference the None load_defect returns for it.
    router.message.outer_middleware(StaleSchemaMiddleware())
    router.callback_query.outer_middleware(StaleSchemaMiddleware())

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

    # Fallbacks, in PTB's order: /cancel, the Cancel button, then a catch-all
    # that silently absorbs anything else while the flow is running.
    msg(cancel_defect_command, StateFilter(DefectSG), Command("cancel"))
    cb(cancel_defect_button, StateFilter(DefectSG), F.data == CB_CANCEL)
    cb(stale_callback, StateFilter(DefectSG))

    return router


def get_defect_entry_router() -> Router:
    """The two ways in. Included after the flow router."""
    router = Router(name="defect_entry")
    router.message.register(new_defect_start, Command("new_defect"))
    router.message.register(new_defect_start, F.text == str(BTN_NEW_DEFECT))
    return router
