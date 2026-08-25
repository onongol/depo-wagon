from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from apps.bot.callbacks import StatusPickCB, StatusSetCB, TasksPageCB
from apps.bot.constants import BTN_OPEN_DEFECTS

from .list import my_tasks
from .status import set_defect_status, show_status_picker


def get_tasks_handlers() -> list:
    return [
        CommandHandler("my_tasks", my_tasks),
        MessageHandler(filters.Text(str(BTN_OPEN_DEFECTS)), my_tasks),
        CallbackQueryHandler(my_tasks, pattern=lambda d: isinstance(d, TasksPageCB)),
        CallbackQueryHandler(
            show_status_picker, pattern=lambda d: isinstance(d, StatusPickCB)
        ),
        CallbackQueryHandler(
            set_defect_status, pattern=lambda d: isinstance(d, StatusSetCB)
        ),
    ]
