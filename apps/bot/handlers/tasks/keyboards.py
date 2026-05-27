from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import BTN_BACK, BTN_NEXT, BTN_PREV, PAGE_SIZE, STATUS_OPTIONS


def tasks_keyboard(defects: list, page: int, total: int) -> InlineKeyboardMarkup:
    """Pagination + one status-change button per defect."""
    buttons = []

    for d in defects:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"🔄 {d.wagon.number} — {d.get_node_display()}",
                    callback_data=f"status_pick:{d.id}:{page}",
                )
            ]
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(str(BTN_PREV), callback_data=f"tasks:{page - 1}"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(str(BTN_NEXT), callback_data=f"tasks:{page + 1}"))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(buttons)


def status_picker_keyboard(defect_id: str, page: str) -> InlineKeyboardMarkup:
    """Status options keyboard for a specific defect."""
    buttons = [
        [
            InlineKeyboardButton(
                str(label), callback_data=f"status_set:{defect_id}:{value}:{page}"
            )
        ]
        for label, value in STATUS_OPTIONS
    ]
    buttons.append(
        [InlineKeyboardButton(str(BTN_BACK), callback_data=f"tasks:{page}")]
    )
    return InlineKeyboardMarkup(buttons)
