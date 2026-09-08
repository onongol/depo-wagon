from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from apps.bot.callback_data import (
    CB_CANCEL,
    CB_MEAS_ADD,
    CB_MEAS_DONE,
    CB_MEAS_SKIP,
    CB_NOOP,
    CB_RESP_EMP_SKIP,
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
from apps.bot.constants import (
    BTN_ADD,
    BTN_CANCEL,
    BTN_DONE,
    BTN_SAVE,
    BTN_SKIP,
    EDIT_FIELDS,
    SEVERITY_CHOICES,
    VERDICT_CHOICES,
)
from apps.bot.keyboards.utils import build_grid_keyboard
from apps.core.constants import Department
from apps.defects.constants import (
    DEPARTMENT_NODES,
    DefectNode,
    DefectType,
    MeasurementDimension,
)


def _cancel_row() -> list[InlineKeyboardButton]:
    """Bottom row with a Cancel button to exit the conversation from any step."""
    return [InlineKeyboardButton(text=str(BTN_CANCEL), callback_data=CB_CANCEL)]


# --- STEP REGISTRATION DEFECT ---


def department_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        Department.choices, DepartmentCB, columns=2, footer=_cancel_row()
    )


def node_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        DefectNode.choices, NodeCB, columns=2, footer=_cancel_row()
    )


def node_keyboard_for_department(department: str) -> InlineKeyboardMarkup:
    nodes = DEPARTMENT_NODES.get(department, list(DefectNode))
    choices = [(n.value, n.label) for n in nodes]
    return build_grid_keyboard(choices, NodeCB, columns=2, footer=_cancel_row())


def defect_type_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        DefectType.choices, DefectTypeCB, columns=3, footer=_cancel_row()
    )


def severity_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=str(label), callback_data=SeverityCB(value=value).pack()
            )
        ]
        for label, value in SEVERITY_CHOICES
    ]
    buttons.append(_cancel_row())
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- PAGINATION AND RESPONSIBLE EMPLOYEE ---


def responsible_employee_keyboard(
    page_employees: list,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Build the inline keyboard for responsible employee selection with pagination."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{emp.first_name} {emp.last_name}",
                callback_data=ResponsibleEmployeeCB(employee_id=emp.id).pack(),
            )
        ]
        for emp in page_employees
    ]

    if total_pages > 1:
        # Fixed 3-slot nav row: absent arrows become spacers so button widths
        # stay stable and the layout doesn't jump between pages. The spacers
        # carry CB_NOOP, which has its own handler — falling through to the
        # expired-button reply would destroy the list on a blank tap.
        if page > 0:
            prev_btn = InlineKeyboardButton(
                text="◀️",
                callback_data=ResponsibleEmployeePageCB(page=page - 1).pack(),
            )
        else:
            prev_btn = InlineKeyboardButton(text=" ", callback_data=CB_NOOP)

        page_btn = InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}", callback_data=CB_NOOP
        )

        if page < total_pages - 1:
            next_btn = InlineKeyboardButton(
                text="▶️",
                callback_data=ResponsibleEmployeePageCB(page=page + 1).pack(),
            )
        else:
            next_btn = InlineKeyboardButton(text=" ", callback_data=CB_NOOP)

        buttons.append([prev_btn, page_btn, next_btn])

    buttons.append(
        [InlineKeyboardButton(text=str(BTN_SKIP), callback_data=CB_RESP_EMP_SKIP)]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- MEASUREMENT AND DIMENSION ---


def dimension_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        MeasurementDimension.choices, DimensionCB, columns=2, footer=_cancel_row()
    )


def measurement_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=str(BTN_ADD), callback_data=CB_MEAS_ADD),
                InlineKeyboardButton(text=str(BTN_SKIP), callback_data=CB_MEAS_SKIP),
            ]
        ]
    )


def measurement_next_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=str(BTN_ADD), callback_data=CB_MEAS_ADD),
                InlineKeyboardButton(text=str(BTN_DONE), callback_data=CB_MEAS_DONE),
            ]
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    edit_buttons = [
        InlineKeyboardButton(text=str(label), callback_data=EditCB(field=key).pack())
        for key, label in EDIT_FIELDS
    ]
    rows = [edit_buttons[i : i + 2] for i in range(0, len(edit_buttons), 2)]
    rows.append(
        [
            InlineKeyboardButton(
                text=str(BTN_SAVE), callback_data=ConfirmCB(confirmed=True).pack()
            ),
            InlineKeyboardButton(
                text=str(BTN_CANCEL), callback_data=ConfirmCB(confirmed=False).pack()
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- POST-EDIT: Added employee verdict keyboard ---


def employee_verdict_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=str(label), callback_data=VerdictCB(value=value).pack()
            )
        ]
        for value, label in VERDICT_CHOICES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
