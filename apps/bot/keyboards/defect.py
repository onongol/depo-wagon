from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from apps.bot.callbacks import (
    ConfirmCB,
    DefectTypeCB,
    DepartmentCB,
    DimensionCB,
    MeasurementAddCB,
    MeasurementDoneCB,
    MeasurementSkipCB,
    NodeCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    ResponsibleEmployeeSkipCB,
    SeverityCB,
    VerdictCB,
)
from apps.bot.constants import (
    BTN_ADD,
    BTN_CANCEL,
    BTN_DONE,
    BTN_SAVE,
    BTN_SKIP,
    SEVERITY_CHOICES,
    VERDICT_CHOICES,
)
from apps.bot.keyboards.utils import build_grid_keyboard
from apps.core.constants import Department
from apps.defects.constants import DefectNode, DefectType


def department_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(Department.choices, DepartmentCB, columns=2)


def node_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(DefectNode.choices, NodeCB, columns=2)


def node_keyboard_for_department(department: str) -> InlineKeyboardMarkup:
    from apps.defects.constants import DEPARTMENT_NODES

    nodes = DEPARTMENT_NODES.get(department, list(DefectNode))
    choices = [(n.value, n.label) for n in nodes]
    return build_grid_keyboard(choices, NodeCB, columns=2)


RESP_EMP_PAGE_SIZE = 5


def responsible_employee_keyboard(
    page_employees: list,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Build the inline keyboard for responsible employee selection with pagination."""
    buttons = [
        [
            InlineKeyboardButton(
                f"{e.first_name} {e.last_name}",
                callback_data=ResponsibleEmployeeCB(employee_id=e.id),
            )
        ]
        for e in page_employees
    ]

    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(
                InlineKeyboardButton(
                    "◀️", callback_data=ResponsibleEmployeePageCB(page=page - 1)
                )
            )
        nav.append(
            InlineKeyboardButton(
                f"{page + 1}/{total_pages}",
                callback_data=ResponsibleEmployeePageCB(page=page),
            )
        )
        if page < total_pages - 1:
            nav.append(
                InlineKeyboardButton(
                    "▶️", callback_data=ResponsibleEmployeePageCB(page=page + 1)
                )
            )
        buttons.append(nav)

    buttons.append(
        [InlineKeyboardButton(str(BTN_SKIP), callback_data=ResponsibleEmployeeSkipCB())]
    )
    return InlineKeyboardMarkup(buttons)


def defect_type_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(DefectType.choices, DefectTypeCB, columns=3)


def dimension_keyboard() -> InlineKeyboardMarkup:
    from apps.defects.constants import MeasurementDimension

    return build_grid_keyboard(MeasurementDimension.choices, DimensionCB, columns=2)


def severity_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(str(label), callback_data=SeverityCB(value))]
        for label, value in SEVERITY_CHOICES
    ]
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    str(BTN_SAVE), callback_data=ConfirmCB(confirmed=True)
                ),
                InlineKeyboardButton(
                    str(BTN_CANCEL), callback_data=ConfirmCB(confirmed=False)
                ),
            ]
        ]
    )


def measurement_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(str(BTN_ADD), callback_data=MeasurementAddCB()),
                InlineKeyboardButton(str(BTN_SKIP), callback_data=MeasurementSkipCB()),
            ]
        ]
    )


def measurement_next_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(str(BTN_ADD), callback_data=MeasurementAddCB()),
                InlineKeyboardButton(str(BTN_DONE), callback_data=MeasurementDoneCB()),
            ]
        ]
    )


def employee_verdict_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(str(label), callback_data=VerdictCB(value))]
        for value, label in VERDICT_CHOICES
    ]
    return InlineKeyboardMarkup(buttons)
