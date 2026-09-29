from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import ConfirmCB, EditCB, VerdictCB
from apps.bot.constants import (
    BTN_CANCEL,
    BTN_SAVE,
    EDIT_FIELDS,
    EDIT_MEASUREMENTS,
    EDIT_RESPONSIBLE,
    VERDICT_CHOICES,
)
from apps.bot.keyboards.utils import build_grid_keyboard
from apps.defects.constants import DefectType

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup

    from apps.bot.user_data import DefectData


def confirm_keyboard(defect: DefectData) -> InlineKeyboardMarkup:
    human_factor = defect.defect_type == DefectType.HUMAN_FACTOR
    builder = InlineKeyboardBuilder()
    for key, label in EDIT_FIELDS:
        if key == EDIT_RESPONSIBLE and not human_factor:
            continue
        if key == EDIT_MEASUREMENTS and human_factor:
            continue
        builder.button(text=str(label), callback_data=EditCB(field=key))

    builder.adjust(2)

    footer = InlineKeyboardBuilder()
    footer.button(text=str(BTN_SAVE), callback_data=ConfirmCB(confirmed=True))
    footer.button(text=str(BTN_CANCEL), callback_data=ConfirmCB(confirmed=False))
    footer.adjust(1)
    builder.attach(footer)

    return builder.as_markup()


def employee_verdict_keyboard() -> InlineKeyboardMarkup:
    return build_grid_keyboard(
        [(label, VerdictCB(value=value)) for value, label in VERDICT_CHOICES],
        columns=1,
    )
