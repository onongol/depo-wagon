from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.users.views_login_link import login_link

urlpatterns = [
    path("admin/", admin.site.urls),
    # One-time sign-in links the Telegram bot hands out. Kept out of
    # /accounts/ so it is never mistaken for an allauth-provided route.
    path("auth/link/<str:token>/", login_link, name="login_link"),
    # Before apps.web.urls: that one is mounted at the root and would otherwise
    # shadow /accounts/… if a matching route were ever added there.
    path("accounts/", include("allauth.urls")),
    path("", include("apps.web.urls")),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.defects.urls")),
    path("api/v1/bot/", include("apps.bot.urls")),
]

if settings.DEBUG:
    import debug_toolbar
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"
        ),
        path("__debug__/", include(debug_toolbar.urls)),
        path("__reload__/", include("django_browser_reload.urls")),
        path("api-auth/", include("rest_framework.urls")),
    ]
