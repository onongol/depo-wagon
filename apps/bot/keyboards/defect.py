from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import (
    CB_DEFECT_CONTINUE,
    CB_DEFECT_RESTART,
    DefectTypeCB,
    DepartmentCB,
    NodeCB,
    SeverityCB,
)
from apps.bot.constants import BTN_CONTINUE, BTN_START_OVER, SEVERITY_CHOICES
from apps.bot.keyboards.common import cancel_row
from apps.bot.keyboards.utils import build_grid_keyboard
from apps.core.constants import Department
from apps.defects.constants import DEPARTMENT_NODES, DefectNode, DefectType

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup


def defect_in_progress_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=str(BTN_CONTINUE), callback_data=CB_DEFECT_CONTINUE)
    builder.button(text=str(BTN_START_OVER), callback_data=CB_DEFECT_RESTART)
    return builder.as_markup()


def department_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        [(label, DepartmentCB(value=value)) for value, label in Department.choices],
        columns=2,
        footer=cancel_row(),
    )


def node_keyboard_for_department(department: str) -> InlineKeyboardMarkup:
    nodes = DEPARTMENT_NODES.get(department, list(DefectNode))
    return build_grid_keyboard(
        [(node.label, NodeCB(value=node.value)) for node in nodes],
        columns=2,
        footer=cancel_row(),
    )


def defect_type_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        [(label, DefectTypeCB(value=value)) for value, label in DefectType.choices],
        columns=3,
        footer=cancel_row(),
    )


def severity_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        [(label, SeverityCB(value=value)) for label, value in SEVERITY_CHOICES],
        columns=1,
        footer=cancel_row(),
    )
