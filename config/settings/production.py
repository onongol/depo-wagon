from config.settings.base import *

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# Same-origin POSTs pass on the host alone; this matters when a form is served
# from another host than Django sees, which is exactly what a proxy can cause.
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        f"https://*{host}" if host.startswith(".") else f"https://{host}"
        for host in ALLOWED_HOSTS
    ],
)

DATABASES["default"]["CONN_MAX_AGE"] = 60

# Email — real Gmail SMTP in production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
# Django has no timeout by default, so one hung SMTP connection pins a worker.
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=5)

# Behind the TLS terminator every request reaches Django as plain HTTP, so
# without this SECURE_SSL_REDIRECT would redirect forever. Set the variable to
# false if gunicorn is ever reachable directly: the header can then be spoofed.
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if env.bool("USE_X_FORWARDED_PROTO", default=True)
    else None
)

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# Scheme for the links allauth mails out; the host comes from the request.
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_NAME = "__Secure-sessionid"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_NAME = "__Secure-csrftoken"
# No JS reads this cookie; every form uses {% csrf_token %}.
CSRF_COOKIE_HTTPONLY = True

MIDDLEWARE = [*MIDDLEWARE, AXES_MIDDLEWARE_PATH]
assert MIDDLEWARE[-1] == AXES_MIDDLEWARE_PATH, "AxesMiddleware must be last"

_LOGS_DIR = BASE_DIR / "logs"
_LOGS_DIR.mkdir(exist_ok=True)

LOGGING["handlers"].update(
    {
        "file_app": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(_LOGS_DIR / "app.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "file_errors": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(_LOGS_DIR / "errors.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
            "level": "ERROR",
        },
    }
)
LOGGING["loggers"]["django"]["handlers"] = ["console", "file_app"]
LOGGING["loggers"]["celery"]["handlers"] = ["console", "file_app"]
LOGGING["loggers"]["apps"]["handlers"] = ["console", "file_app"]
LOGGING["root"]["handlers"] = ["console", "file_errors"]
