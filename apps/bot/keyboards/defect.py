from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from apps.bot.keyboards.utils import build_grid_keyboard
from apps.bot.callbacks import (
    ConfirmCB,
    DefectTypeCB,
    DimensionCB,
    MeasurementAddCB,
    MeasurementDoneCB,
    MeasurementSkipCB,
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
    SEVERITY_CHOICES,
    VERDICT_CHOICES,
)
from apps.defects.constants import DefectNode, DefectType


def node_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(DefectNode.choices, NodeCB, columns=2)


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
