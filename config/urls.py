from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.users.views_login_link import login_link

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    # One-time sign-in links the Telegram bot hands out. Kept out of
    # /accounts/ so it is never mistaken for an allauth-provided route.
    path("auth/link/<str:token>/", login_link, name="login_link"),
    # Before apps.web.urls: that one is mounted at the root and would otherwise
    # shadow /accounts/… if a matching route were ever added there.
    path("accounts/", include("allauth.urls")),
    path("_allauth/", include("allauth.headless.urls")),
    path("", include("apps.web.urls")),
    path("api/v1/bot/", include("apps.bot.urls")),
    path("api/v1/", include("config.api_router")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
        path("__reload__/", include("django_browser_reload.urls")),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
