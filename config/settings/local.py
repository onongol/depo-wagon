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
    # First, so its runserver shadows the one staticfiles installs.
    "whitenoise.runserver_nostatic",
    *INSTALLED_APPS,
    "debug_toolbar",
    "django_browser_reload",
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    *MIDDLEWARE,
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]
if AXES_MIDDLEWARE_PATH in MIDDLEWARE:
    MIDDLEWARE.remove(AXES_MIDDLEWARE_PATH)
MIDDLEWARE.append(AXES_MIDDLEWARE_PATH)

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

# CELERY
# ------------------------------------------------------------------------------
# Let a task's own output through: the console email backend writes to stdout,
# which the worker otherwise swallows into its logger.
CELERY_WORKER_REDIRECT_STDOUTS = False

# LOGGING
# ------------------------------------------------------------------------------
# Show all SQL queries in the console during development
LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"

# allauth.headless
# ------------------------------------------------------------------------------
# Account endpoints are outside the drf-spectacular schema; allauth ships its own.
HEADLESS_SERVE_SPECIFICATION = True
# Swagger over the default redoc: these endpoints are POST-only, so a console beats a listing.
HEADLESS_SPECIFICATION_TEMPLATE_NAME = "headless/spec/swagger_cdn.html"

# django-debug-toolbar
# ------------------------------------------------------------------------------
INTERNAL_IPS = env.list("INTERNAL_IPS", cast=str.strip, default=["127.0.0.1", "::1"])
