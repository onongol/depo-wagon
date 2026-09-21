from aiogram import F, Router
from aiogram.filters import Command

from apps.bot.callback_data import (
    DefectCardCB,
    StatusAskCB,
    StatusPickCB,
    StatusSetCB,
    TasksPageCB,
)
from apps.bot.constants import BTN_OPEN_DEFECTS

from .card import show_defect_card
from .list import my_tasks, my_tasks_page
from .status import ask_status_confirmation, set_defect_status, show_status_picker


def get_tasks_router() -> Router:
    """The open-defects list and card. Not a conversation — every tap re-queries."""
    router = Router(name="tasks")
    router.message.register(my_tasks, Command("my_tasks"))
    router.message.register(my_tasks, F.text == str(BTN_OPEN_DEFECTS))
    router.callback_query.register(my_tasks_page, TasksPageCB.filter())
    router.callback_query.register(show_defect_card, DefectCardCB.filter())
    router.callback_query.register(show_status_picker, StatusPickCB.filter())
    router.callback_query.register(ask_status_confirmation, StatusAskCB.filter())
    router.callback_query.register(set_defect_status, StatusSetCB.filter())
    return router
