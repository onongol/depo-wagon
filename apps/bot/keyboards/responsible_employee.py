from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import (
    CB_NOOP,
    CB_RESP_EMP_ALL,
    CB_RESP_EMP_SKIP,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
)
from apps.bot.constants import (
    BTN_ALL_EMPLOYEES,
    BTN_PAGE_NEXT,
    BTN_PAGE_PREV,
    BTN_SKIP,
)

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup


def _pagination_row(page: int, total_pages: int) -> InlineKeyboardBuilder:
    """Fixed 3-slot nav row: page prev, page counter, page next.

    Absent arrows become spacers so button widths stay stable and the layout
    doesn't jump between pages. The spacers carry CB_NOOP, which has its own
    handler — falling through to the expired-button reply would destroy the
    list on a blank tap.
    """
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(
            text=BTN_PAGE_PREV,
            callback_data=ResponsibleEmployeePageCB(page=page - 1),
        )
    else:
        nav.button(text=" ", callback_data=CB_NOOP)

    nav.button(text=f"{page + 1}/{total_pages}", callback_data=CB_NOOP)

    if page < total_pages - 1:
        nav.button(
            text=BTN_PAGE_NEXT,
            callback_data=ResponsibleEmployeePageCB(page=page + 1),
        )
    else:
        nav.button(text=" ", callback_data=CB_NOOP)

    return nav


def responsible_employee_keyboard(
    page_employees: list,
    page: int,
    total_pages: int,
    *,
    searching: bool = False,
) -> InlineKeyboardMarkup:
    """Build the inline keyboard for responsible employee selection with pagination."""
    builder = InlineKeyboardBuilder()
    for emp in page_employees:
        builder.button(
            text=f"{emp.first_name} {emp.last_name}",
            callback_data=ResponsibleEmployeeCB(employee_id=emp.id),
        )
    builder.adjust(1)

    if total_pages > 1:
        builder.attach(_pagination_row(page, total_pages))

    if searching:
        builder.row(
            InlineKeyboardButton(
                text=str(BTN_ALL_EMPLOYEES), callback_data=CB_RESP_EMP_ALL
            )
        )
    builder.row(
        InlineKeyboardButton(text=str(BTN_SKIP), callback_data=CB_RESP_EMP_SKIP)
    )
    return builder.as_markup()
