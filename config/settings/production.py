from decouple import Csv, config

from config.settings.base import *

DEBUG = False
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

DATABASES["default"]["CONN_MAX_AGE"] = 60

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

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
