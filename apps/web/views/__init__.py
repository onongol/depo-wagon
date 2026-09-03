from apps.web.views.account import account_overview, end_user_session
from apps.web.views.dashboard import dashboard
from apps.web.views.defects import defect_list
from apps.web.views.documents import document_list
from apps.web.views.employees import employee_list
from apps.web.views.home import home
from apps.web.views.telegram import telegram_connect, telegram_disconnect
from apps.web.views.wagons import wagon_add, wagon_delete_bulk, wagon_edit, wagon_list

__all__ = [
    "account_overview",
    "dashboard",
    "defect_list",
    "document_list",
    "employee_list",
    "end_user_session",
    "home",
    "telegram_connect",
    "telegram_disconnect",
    "wagon_add",
    "wagon_delete_bulk",
    "wagon_edit",
    "wagon_list",
]
