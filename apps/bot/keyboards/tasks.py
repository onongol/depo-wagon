from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import StatusPickCB, StatusSetCB, TasksPageCB
from apps.bot.constants import (
    BTN_BACK,
    BTN_NEXT,
    BTN_PREV,
    STATUS_CHANGE_EMOJI,
    STATUS_OPTIONS,
    TASKS_PAGE_SIZE,
)

if TYPE_CHECKING:
    import uuid

    from aiogram.types import InlineKeyboardMarkup


def _pagination_row_tasks(page: int, total: int) -> InlineKeyboardBuilder:
    """Previous/Next row; each arrow appears only when there is a page to go to."""
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text=str(BTN_PREV), callback_data=TasksPageCB(page=page - 1))
    if (page + 1) * TASKS_PAGE_SIZE < total:
        nav.button(text=str(BTN_NEXT), callback_data=TasksPageCB(page=page + 1))
    return nav


def tasks_keyboard(
    defects: list, page: int, total: int, *, can_change_status: bool = False
) -> InlineKeyboardMarkup:
    """Build a keyboard for displaying tasks with optional status change buttons."""
    builder = InlineKeyboardBuilder()
    if can_change_status:
        for defect in defects:
            builder.button(
                text=(
                    f"{STATUS_CHANGE_EMOJI} {defect.wagon.number} — "
                    f"{defect.get_node_display()}"
                ),
                callback_data=StatusPickCB(defect_id=defect.id, page=page),
            )
        builder.adjust(1)

    builder.attach(_pagination_row_tasks(page, total))

    return builder.as_markup()


def status_picker_keyboard(defect_id: uuid.UUID, page: int) -> InlineKeyboardMarkup:
    """Status options keyboard for a specific defect."""
    builder = InlineKeyboardBuilder()
    for label, value in STATUS_OPTIONS:
        builder.button(
            text=str(label),
            callback_data=StatusSetCB(defect_id=defect_id, status=value, page=page),
        )
    builder.button(text=str(BTN_BACK), callback_data=TasksPageCB(page=page))
    builder.adjust(1)

    return builder.as_markup()
