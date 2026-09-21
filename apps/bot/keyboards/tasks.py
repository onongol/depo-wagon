from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.callback_data import (
    DefectCardCB,
    StatusAskCB,
    StatusPickCB,
    StatusSetCB,
    TasksPageCB,
)
from apps.bot.constants import (
    BTN_BACK,
    BTN_CANCEL,
    BTN_CHANGE_STATUS,
    BTN_CONFIRM,
    BTN_NEXT,
    BTN_PREV,
    LIST_NUMBER_EMOJI,
    STATUS_LABEL,
    TASKS_PAGE_SIZE,
)

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable

    from aiogram.types import InlineKeyboardMarkup

    from apps.defects.constants import DefectStatus


def _pagination_row_tasks(page: int, pages: int) -> InlineKeyboardBuilder:
    """Previous/Next row; each arrow appears only when there is a page to go to."""
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text=str(BTN_PREV), callback_data=TasksPageCB(page=page - 1))
    if page + 1 < pages:
        nav.button(text=str(BTN_NEXT), callback_data=TasksPageCB(page=page + 1))
    return nav


def tasks_keyboard(defects: list, page: int, pages: int) -> InlineKeyboardMarkup:
    """A row of the list's numbers, each opening its card, then the page arrows."""
    builder = InlineKeyboardBuilder()
    for keycap, defect in zip(LIST_NUMBER_EMOJI, defects, strict=False):
        builder.button(
            text=keycap, callback_data=DefectCardCB(defect_id=defect.id, page=page)
        )
    builder.adjust(TASKS_PAGE_SIZE)

    builder.attach(_pagination_row_tasks(page, pages))

    return builder.as_markup()


def defect_card_keyboard(
    defect_id: uuid.UUID, page: int, *, can_change: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_change:
        builder.button(
            text=str(BTN_CHANGE_STATUS),
            callback_data=StatusPickCB(defect_id=defect_id, page=page),
        )
    builder.button(text=str(BTN_BACK), callback_data=TasksPageCB(page=page))
    builder.adjust(1)

    return builder.as_markup()


def status_picker_keyboard(
    defect_id: uuid.UUID, targets: Iterable[DefectStatus], page: int
) -> InlineKeyboardMarkup:
    """The statuses this defect may move to, and a way back to its card."""
    builder = InlineKeyboardBuilder()
    for status in targets:
        builder.button(
            text=str(STATUS_LABEL[status]),
            callback_data=StatusAskCB(defect_id=defect_id, status=status, page=page),
        )
    builder.button(
        text=str(BTN_BACK), callback_data=DefectCardCB(defect_id=defect_id, page=page)
    )
    builder.adjust(1)

    return builder.as_markup()


def status_confirm_keyboard(
    defect_id: uuid.UUID, status: DefectStatus, page: int
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=str(BTN_CONFIRM),
        callback_data=StatusSetCB(defect_id=defect_id, status=status, page=page),
    )
    builder.button(
        text=str(BTN_CANCEL),
        callback_data=DefectCardCB(defect_id=defect_id, page=page),
    )

    return builder.as_markup()
