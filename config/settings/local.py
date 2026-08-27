from config.settings.base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Needed for a tunnel (ngrok, cloudflared) in front of runserver: the origin is
# then https on someone else's host, which Django rejects for POSTs otherwise.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Cookies don't need Secure over plain HTTP locally
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

INSTALLED_APPS = [
    *INSTALLED_APPS,
    "whitenoise.runserver_nostatic",
    "debug_toolbar",
    "django_browser_reload",
]

MIDDLEWARE = [
    *MIDDLEWARE,
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    AXES_MIDDLEWARE_PATH,
]
assert MIDDLEWARE[-1] == AXES_MIDDLEWARE_PATH, "AxesMiddleware must be last"

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

DATABASES["default"]["CONN_MAX_AGE"] = 0

# Show all SQL queries in the console during development
LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"
