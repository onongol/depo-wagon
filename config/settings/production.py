import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from config.settings.base import *

# REQUIRED CONFIGURATION
# ------------------------------------------------------------------------------
for _name in (
    "SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "DJANGO_ADMIN_URL",
    "DEFAULT_FROM_EMAIL",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_STORAGE_BUCKET_NAME",
    "AWS_S3_ENDPOINT_URL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_FSM_REDIS_URL",
    "GOOGLE_AI_KEY",
):
    if not env(_name, default=""):
        msg = f"{_name} environment variable not set"
        raise ImproperlyConfigured(msg)

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", cast=str.strip, default=[])
if not ALLOWED_HOSTS:
    msg = "ALLOWED_HOSTS environment variable not set"
    raise ImproperlyConfigured(msg)

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = 60
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# TEMPLATES
# ------------------------------------------------------------------------------
# Django wraps the loaders itself only when they are left unset; base.py sets them.
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    ("django.template.loaders.cached.Loader", TEMPLATES[0]["OPTIONS"]["loaders"])
]

# SECURITY
# ------------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", cast=str.strip, default=[])
if not CSRF_TRUSTED_ORIGINS:
    msg = "CSRF_TRUSTED_ORIGINS environment variable not set"
    raise ImproperlyConfigured(msg)

SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if env.bool("USE_X_FORWARDED_PROTO", default=True)
    else None
)

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)

# Start at 60s; raise to 518400 (6 days) once HSTS is confirmed working.
SECURE_HSTS_SECONDS = 60
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_NAME = "__Secure-sessionid"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_NAME = "__Secure-csrftoken"

# EMAIL
# ------------------------------------------------------------------------------
# Real Gmail SMTP in production, reached from the Celery worker rather than a request.
EMAIL_BACKEND = "apps.core.mail.CeleryEmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=5)

# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

# sentry-sdk
# ------------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        release=env("SENTRY_RELEASE", default=None),
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        send_default_pii=False,
    )
