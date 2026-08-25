from apps.web.views.auth import login_view, logout_view
from apps.web.views.dashboard import dashboard
from apps.web.views.defects import defect_list
from apps.web.views.documents import document_list
from apps.web.views.employees import employee_list
from apps.web.views.home import home
from apps.web.views.wagons import wagon_add, wagon_delete_bulk, wagon_edit, wagon_list

__all__ = [
    "login_view",
    "logout_view",
    "home",
    "dashboard",
    "wagon_list",
    "wagon_add",
    "wagon_edit",
    "wagon_delete_bulk",
    "defect_list",
    "employee_list",
    "document_list",
]
