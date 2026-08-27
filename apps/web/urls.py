from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    # Login and logout are served by allauth under /accounts/ — see
    # config.urls and the `account_login` / `account_logout` URL names. This
    # page is the index into those, which allauth does not provide.
    path("account/", views.account_overview, name="account_overview"),
    path(
        "account/sessions/<int:session_id>/end/",
        views.end_user_session,
        name="end_user_session",
    ),
    path("wagons/", views.wagon_list, name="wagon_list"),
    path("wagons/add/", views.wagon_add, name="wagon_add"),
    path("wagons/<int:pk>/edit/", views.wagon_edit, name="wagon_edit"),
    path("wagons/delete/", views.wagon_delete_bulk, name="wagon_delete_bulk"),
    path("defects/", views.defect_list, name="defect_list"),
    path("employees/", views.employee_list, name="employee_list"),
    path("documents/", views.document_list, name="document_list"),
    path("telegram/", views.telegram_connect, name="telegram_connect"),
    path(
        "telegram/disconnect/",
        views.telegram_disconnect,
        name="telegram_disconnect",
    ),
]
