from config.settings.base import *

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = True
ALLOWED_HOSTS = ["*"]

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = 0

# APPS
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",
    *INSTALLED_APPS,
    "debug_toolbar",
    "django_browser_reload",
]
assert INSTALLED_APPS.index("whitenoise.runserver_nostatic") < INSTALLED_APPS.index(
    "django.contrib.staticfiles"
), "runserver_nostatic must precede staticfiles"

# MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    *MIDDLEWARE,
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    AXES_MIDDLEWARE_PATH,
]
assert MIDDLEWARE[-1] == AXES_MIDDLEWARE_PATH, "AxesMiddleware must be last"

# MEDIA
# ------------------------------------------------------------------------------
# R2 only on demand: it is the one place presigned URLs and CORS actually show up.
if not env.bool("USE_R2", default=False):
    STORAGES = {
        **STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }

# SECURITY
# ------------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Cookies don't need Secure over plain HTTP locally
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# EMAIL
# ------------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# LOGGING
# ------------------------------------------------------------------------------
# Show all SQL queries in the console during development
LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"

# django-debug-toolbar
# ------------------------------------------------------------------------------
INTERNAL_IPS = env.list("INTERNAL_IPS", cast=str.strip, default=["127.0.0.1", "::1"])
