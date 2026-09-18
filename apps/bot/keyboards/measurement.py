from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import CB_MEAS_ADD, CB_MEAS_DONE, CB_MEAS_SKIP, DimensionCB
from apps.bot.constants import BTN_ADD, BTN_DONE, BTN_SKIP
from apps.bot.keyboards.common import cancel_row
from apps.bot.keyboards.utils import build_grid_keyboard
from apps.defects.constants import MeasurementDimension

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup


def dimension_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        [
            (label, DimensionCB(value=value))
            for value, label in MeasurementDimension.choices
        ],
        columns=2,
        footer=cancel_row(),
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
