from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import (
    CB_CANCEL,
    CB_MEAS_ADD,
    CB_MEAS_DONE,
    CB_MEAS_SKIP,
    ConfirmCB,
    DefectTypeCB,
    DepartmentCB,
    DimensionCB,
    EditCB,
    NodeCB,
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

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup


def _cancel_row() -> list[InlineKeyboardButton]:
    """Bottom row with a Cancel button to exit the conversation from any step."""
    return [InlineKeyboardButton(text=str(BTN_CANCEL), callback_data=CB_CANCEL)]


# --- STEP REGISTRATION DEFECT ---


def department_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        [(label, DepartmentCB(value=value)) for value, label in Department.choices],
        columns=2,
        footer=_cancel_row(),
    )


def node_keyboard_for_department(department: str) -> InlineKeyboardMarkup:
    nodes = DEPARTMENT_NODES.get(department, list(DefectNode))
    return build_grid_keyboard(
        [(node.label, NodeCB(value=node.value)) for node in nodes],
        columns=2,
        footer=_cancel_row(),
    )


def defect_type_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        [(label, DefectTypeCB(value=value)) for value, label in DefectType.choices],
        columns=3,
        footer=_cancel_row(),
    )


def severity_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        [(label, SeverityCB(value=value)) for label, value in SEVERITY_CHOICES],
        columns=1,
        footer=_cancel_row(),
    )


# --- MEASUREMENT AND DIMENSION ---


def dimension_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        [
            (label, DimensionCB(value=value))
            for value, label in MeasurementDimension.choices
        ],
        columns=2,
        footer=_cancel_row(),
    )


def measurement_choice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=str(BTN_ADD), callback_data=CB_MEAS_ADD)
    builder.button(text=str(BTN_SKIP), callback_data=CB_MEAS_SKIP)
    return builder.as_markup()


def measurement_next_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=str(BTN_ADD), callback_data=CB_MEAS_ADD)
    builder.button(text=str(BTN_DONE), callback_data=CB_MEAS_DONE)
    return builder.as_markup()


# --- SUMMARY AND CONFIRM ---


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in EDIT_FIELDS:
        builder.button(text=str(label), callback_data=EditCB(field=key))

    builder.adjust(2)

    footer = InlineKeyboardBuilder()
    footer.button(text=str(BTN_SAVE), callback_data=ConfirmCB(confirmed=True))
    footer.button(text=str(BTN_CANCEL), callback_data=ConfirmCB(confirmed=False))
    builder.attach(footer)

    return builder.as_markup()


def employee_verdict_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        [(label, VerdictCB(value=value)) for value, label in VERDICT_CHOICES],
        columns=1,
    )
