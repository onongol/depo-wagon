from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("wagons/", views.wagon_list, name="wagon_list"),
    path("wagons/add/", views.wagon_add, name="wagon_add"),
    path("wagons/<int:pk>/edit/", views.wagon_edit, name="wagon_edit"),
    path("wagons/delete/", views.wagon_delete_bulk, name="wagon_delete_bulk"),
    path("defects/", views.defect_list, name="defect_list"),
    path("employees/", views.employee_list, name="employee_list"),
    path("documents/", views.document_list, name="document_list"),
]
