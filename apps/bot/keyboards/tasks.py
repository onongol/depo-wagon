from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from apps.bot.callbacks import StatusPickCB, StatusSetCB, TasksPageCB
from apps.bot.constants import (
    BTN_BACK,
    BTN_NEXT,
    BTN_PREV,
    PAGE_SIZE,
    STATUS_OPTIONS,
)

if TYPE_CHECKING:
    import uuid


def tasks_keyboard(defects: list, page: int, total: int) -> InlineKeyboardMarkup:
    """Pagination + one status-change button per defect."""
    buttons = [
        [
            InlineKeyboardButton(
                f"🔄 {defect.wagon.number} — {defect.get_node_display()}",
                callback_data=StatusPickCB(defect_id=defect.id, page=page),
            )
        ]
        for defect in defects
    ]

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                str(BTN_PREV), callback_data=TasksPageCB(page=page - 1)
            )
        )
    if (page + 1) * PAGE_SIZE < total:
        nav.append(
            InlineKeyboardButton(
                str(BTN_NEXT), callback_data=TasksPageCB(page=page + 1)
            )
        )
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(buttons)


def status_picker_keyboard(defect_id: uuid.UUID, page: int) -> InlineKeyboardMarkup:
    """Status options keyboard for a specific defect."""
    buttons = [
        [
            InlineKeyboardButton(
                str(label),
                callback_data=StatusSetCB(defect_id=defect_id, status=value, page=page),
            )
        ]
        for label, value in STATUS_OPTIONS
    ]

    buttons.append(
        [InlineKeyboardButton(str(BTN_BACK), callback_data=TasksPageCB(page=page))]
    )

    return InlineKeyboardMarkup(buttons)
