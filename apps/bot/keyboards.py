from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from apps.bot.constants import (
    BTN_ADD,
    BTN_CANCEL,
    BTN_DONE,
    BTN_HELP,
    BTN_NEW_DEFECT,
    BTN_OPEN_DEFECTS,
    BTN_SAVE,
    BTN_SKIP,
    SEVERITY_CHOICES,
    VERDICT_CHOICES,
)
from apps.defects.constants import DefectNode, DefectType


def node_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting wagon node (2 columns)."""
    nodes = [(str(label), value) for value, label in DefectNode.choices]
    buttons = []
    for i in range(0, len(nodes), 2):
        row = [InlineKeyboardButton(nodes[i][0], callback_data=f"node:{nodes[i][1]}")]
        if i + 1 < len(nodes):
            row.append(
                InlineKeyboardButton(
                    nodes[i + 1][0], callback_data=f"node:{nodes[i + 1][1]}"
                )
            )
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def defect_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting defect type (2 columns)."""
    types = [(str(label), value) for value, label in DefectType.choices]
    buttons = []
    for i in range(0, len(types), 2):
        row = [InlineKeyboardButton(types[i][0], callback_data=f"dtype:{types[i][1]}")]
        if i + 1 < len(types):
            row.append(
                InlineKeyboardButton(
                    types[i + 1][0], callback_data=f"dtype:{types[i + 1][1]}"
                )
            )
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def severity_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting defect severity."""
    buttons = [
        [InlineKeyboardButton(str(label), callback_data=f"sev:{value}")]
        for label, value in SEVERITY_CHOICES
    ]
    return InlineKeyboardMarkup(buttons)


def skip_keyboard(callback_data: str = "skip") -> InlineKeyboardMarkup:
    """Single 'Skip' button."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(str(BTN_SKIP), callback_data=callback_data)]]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Save / Cancel confirmation keyboard."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(str(BTN_SAVE), callback_data="confirm:yes"),
                InlineKeyboardButton(str(BTN_CANCEL), callback_data="confirm:no"),
            ]
        ]
    )


def measurement_choice_keyboard() -> InlineKeyboardMarkup:
    """Ask whether to add a measurement or skip."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    str(BTN_ADD), callback_data="meas:add"
                ),
                InlineKeyboardButton(str(BTN_SKIP), callback_data="meas:skip"),
            ]
        ]
    )


def measurement_next_keyboard() -> InlineKeyboardMarkup:
    """After saving a measurement: add another or finish."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(str(BTN_ADD), callback_data="meas:add"),
                InlineKeyboardButton(str(BTN_DONE), callback_data="meas:done"),
            ]
        ]
    )


def dimension_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting measurement dimension (2 columns)."""
    from apps.defects.constants import MeasurementDimension

    dims = [(str(label), value) for value, label in MeasurementDimension.choices]
    buttons = []
    for i in range(0, len(dims), 2):
        row = [InlineKeyboardButton(dims[i][0], callback_data=f"dim:{dims[i][1]}")]
        if i + 1 < len(dims):
            row.append(
                InlineKeyboardButton(
                    dims[i + 1][0], callback_data=f"dim:{dims[i + 1][1]}"
                )
            )
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def employee_verdict_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for employee's own verdict after AI analysis."""
    buttons = [
        [InlineKeyboardButton(str(label), callback_data=f"verdict:{value}")]
        for value, label in VERDICT_CHOICES
    ]
    return InlineKeyboardMarkup(buttons)


def main_menu_keyboard(role: str) -> ReplyKeyboardMarkup:
    """Persistent reply keyboard based on employee role."""
    buttons = [[str(BTN_NEW_DEFECT)]]
    if role in ("master", "engineer", "manager"):
        buttons.append([str(BTN_OPEN_DEFECTS)])
    buttons.append([str(BTN_HELP)])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)
