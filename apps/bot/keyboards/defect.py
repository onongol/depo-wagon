from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from apps.bot.callbacks import (
    CancelCB,
    ConfirmCB,
    DefectTypeCB,
    DepartmentCB,
    DimensionCB,
    EditCB,
    MeasurementAddCB,
    MeasurementDoneCB,
    MeasurementSkipCB,
    NodeCB,
    PassCB,
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
    return [InlineKeyboardButton(str(BTN_CANCEL), callback_data=CancelCB())]


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
        [InlineKeyboardButton(str(label), callback_data=SeverityCB(value))]
        for label, value in SEVERITY_CHOICES
    ]
    buttons.append(_cancel_row())
    return InlineKeyboardMarkup(buttons)


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
                f"{emp.first_name} {emp.last_name}",
                callback_data=ResponsibleEmployeeCB(employee_id=emp.id),
            )
        ]
        for emp in page_employees
    ]

    if total_pages > 1:
        # Fixed 3-slot nav row: absent arrows become spacers so button widths
        # stay stable and the layout doesn't jump between pages.
        if page > 0:
            prev_btn = InlineKeyboardButton(
                "◀️", callback_data=ResponsibleEmployeePageCB(page=page - 1)
            )
        else:
            prev_btn = InlineKeyboardButton(" ", callback_data=PassCB())

        page_btn = InlineKeyboardButton(
            f"{page + 1}/{total_pages}", callback_data=PassCB()
        )

        if page < total_pages - 1:
            next_btn = InlineKeyboardButton(
                "▶️", callback_data=ResponsibleEmployeePageCB(page=page + 1)
            )
        else:
            next_btn = InlineKeyboardButton(" ", callback_data=PassCB())

        buttons.append([prev_btn, page_btn, next_btn])

    buttons.append(
        [InlineKeyboardButton(str(BTN_SKIP), callback_data=ResponsibleEmployeeSkipCB())]
    )
    return InlineKeyboardMarkup(buttons)


# --- MEASUREMENT AND DIMENSION ---


def dimension_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        MeasurementDimension.choices, DimensionCB, columns=2, footer=_cancel_row()
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


def confirm_keyboard() -> InlineKeyboardMarkup:
    edit_buttons = [
        InlineKeyboardButton(str(label), callback_data=EditCB(field=key))
        for key, label in EDIT_FIELDS
    ]
    rows = [edit_buttons[i : i + 2] for i in range(0, len(edit_buttons), 2)]
    rows.append(
        [
            InlineKeyboardButton(
                str(BTN_SAVE), callback_data=ConfirmCB(confirmed=True)
            ),
            InlineKeyboardButton(
                str(BTN_CANCEL), callback_data=ConfirmCB(confirmed=False)
            ),
        ]
    )
    return InlineKeyboardMarkup(rows)


# --- POST-EDIT: Added employee verdict keyboard ---


def employee_verdict_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(str(label), callback_data=VerdictCB(value))]
        for value, label in VERDICT_CHOICES
    ]
    return InlineKeyboardMarkup(buttons)
