from decouple import config

from config.settings.base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS += [
    "debug_toolbar",
    "django_browser_reload",
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

INTERNAL_IPS = ["127.0.0.1"]

# Email — Mailtrap sandbox via SMTP (catches all emails, nothing sent to real users)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "sandbox.smtp.mailtrap.io"
EMAIL_PORT = 2525
EMAIL_USE_TLS = False
EMAIL_HOST_USER = config("MAILTRAP_USER", default="")
EMAIL_HOST_PASSWORD = config("MAILTRAP_PASSWORD", default="")

DATABASES["default"]["CONN_MAX_AGE"] = 0

# Show all SQL queries in the console during development
LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"

REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    "knox.auth.TokenAuthentication",
    "rest_framework.authentication.SessionAuthentication",
]
