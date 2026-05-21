from django.urls import path

from apps.users.views import LoginView, LogoutAllView, LogoutView

urlpatterns = [
    path("login/", LoginView.as_view(), name="knox-login"),
    path("logout/", LogoutView.as_view(), name="knox-logout"),
    path("logout-all/", LogoutAllView.as_view(), name="knox-logout-all"),
]
