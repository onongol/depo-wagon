from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import (
    CB_MEAS_BACK,
    CB_MEAS_CLEAR,
    CB_MEAS_DONE,
    CB_MEAS_SKIP,
    DimensionCB,
)
from apps.bot.constants import BTN_BACK, BTN_CLEAR, BTN_DONE, BTN_SKIP
from apps.defects.constants import MeasurementDimension

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup


def measurement_keyboard(
    *, any_saved: bool, clearable: bool = False
) -> InlineKeyboardMarkup:
    """A dimension adds a measurement; Skip turns into Done once one is saved.

    Clear is for an Edit, which reopens the saved ones.
    """
    builder = InlineKeyboardBuilder()
    for value, label in MeasurementDimension.choices:
        builder.button(text=str(label), callback_data=DimensionCB(value=value))
    builder.adjust(2)

    if clearable:
        builder.row(
            InlineKeyboardButton(text=str(BTN_CLEAR), callback_data=CB_MEAS_CLEAR)
        )
    if any_saved:
        builder.row(
            InlineKeyboardButton(text=str(BTN_DONE), callback_data=CB_MEAS_DONE)
        )
    else:
        builder.row(
            InlineKeyboardButton(text=str(BTN_SKIP), callback_data=CB_MEAS_SKIP)
        )
    return builder.as_markup()


def measurement_value_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=str(BTN_BACK), callback_data=CB_MEAS_BACK)
    return builder.as_markup()
