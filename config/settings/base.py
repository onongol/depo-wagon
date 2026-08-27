from datetime import timedelta
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# django-environ reads no .env unless told to, and never overwrites a variable
# already in the process environment. The production image ships without a
# .env, so there this call is a no-op and the environment alone configures it.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Must precede django.contrib.admin: unfold ships replacements for the admin's
# own templates, and template resolution is won by the app listed first.
ADMIN_THEME_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    "unfold.contrib.simple_history",
]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.usersessions",
    "axes",
    "django_filters",
    "rest_framework",
    "knox",
    "drf_spectacular",
    "import_export",
    "simple_history",
    "storages",
    "widget_tweaks",
    "django_components",
]

LOCAL_APPS = [
    "apps.users",
    "apps.core",
    "apps.defects",
    "apps.bot",
    "apps.ai_service",
    "apps.web",
]

INSTALLED_APPS = ADMIN_THEME_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "users.CustomUser"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "allauth.usersessions.middleware.UserSessionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
                "django_components.template_loader.Loader",
            ],
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "builtins": [
                "django_components.templatetags.component_tags",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}

# Celery
CELERY_BROKER_URL = env("REDIS_URL")
CELERY_RESULT_BACKEND = env("REDIS_URL")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

LANGUAGE_CODE = "en"

# Supported languages
LANGUAGES = [
    ("en", _("English")),
    ("mn", _("Mongolian")),
]

TIME_ZONE = "Asia/Ulaanbaatar"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

# Cloudflare R2
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")
AWS_S3_SIGNATURE_VERSION = "s3v4"
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# Email — base config (credentials shared between environments)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("EMAIL_HOST_USER", default="noreply@depowagon.mn")

SITE_URL = env("SITE_URL", default="http://localhost:8000")

# Telegram
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")
TELEGRAM_WEBHOOK_URL = env("TELEGRAM_WEBHOOK_URL", default="")
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")

# The support person must have pressed Start on the bot at least once.
TELEGRAM_SUPPORT_CHAT_ID = env("TELEGRAM_SUPPORT_CHAT_ID", default="")

# Google AI
GOOGLE_AI_KEY = env("GOOGLE_AI_KEY")

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "knox.auth.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Depo Wagon API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "AUTHENTICATION_WHITELIST": [
        "knox.auth.TokenAuthentication",
    ],
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
    "ENUM_NAME_OVERRIDES": {
        "WagonStatusEnum": "apps.core.constants.WagonStatus",
        "DefectStatusEnum": "apps.defects.constants.DefectStatus",
        "DefectVerdictEnum": "apps.defects.constants.DefectVerdict",
    },
}

AUTHENTICATION_BACKENDS = [
    # Must stay first: it is what refuses a locked-out attempt.
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "web:home"
LOGOUT_REDIRECT_URL = "account_login"

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_SIGNUP_FORM_CLASS = "apps.users.forms.EmployeeSignupForm"
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_EMAIL_NOTIFICATIONS = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = True
ACCOUNT_ADAPTER = "apps.users.adapters.AccountAdapter"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Depo Wagon] "
ACCOUNT_SESSION_REMEMBER = False
ACCOUNT_PREVENT_ENUMERATION = True

# Must match the deployment: at 0 the per-IP limits below see only the proxy's address.
ALLAUTH_TRUSTED_PROXY_COUNT = env.int("TRUSTED_PROXY_COUNT", default=0)

ACCOUNT_RATE_LIMITS = {
    "login": "30/m/ip",
    "login_failed": "10/m/ip,5/300s/key",
    "signup": "10/m/ip",
    "confirm_email": "1/180s/key",
    "reset_password": "20/m/ip,5/m/key",
    "reset_password_from_key": "20/m/ip",
    "change_password": "5/m/user",
    "reauthenticate": "10/m/user",
}

AXES_MIDDLEWARE_PATH = "axes.middleware.AxesMiddleware"
# Backstop behind ACCOUNT_RATE_LIMITS: kept in the database, so it survives a
# cache flush, and hooked on the login signal, so it also covers /admin/, which
# allauth's limiter never sees. The limit is above allauth's on purpose — the
# nicer 429 should be what users normally hit.
AXES_FAILURE_LIMIT = 10
AXES_COOLOFF_TIME = timedelta(minutes=30)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_USERNAME_CALLABLE = "apps.users.axes.get_username"
AXES_IPWARE_PROXY_COUNT = ALLAUTH_TRUSTED_PROXY_COUNT or None

USERSESSIONS_TRACK_ACTIVITY = True

# SAVE_EVERY_REQUEST makes the age an idle timeout, counted from the last request.
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True
# Also covers sessions allauth does not create, e.g. the admin's.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

REST_KNOX = {
    "TOKEN_TTL": timedelta(hours=10),
    "AUTO_REFRESH": False,  # no browser-close signal on the API; TTL is the only bound
    "TOKEN_LIMIT_PER_USER": None,
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "pwned_passwords_django.validators.PwnedPasswordsValidator"},
]

# django-allauth: optional two-factor auth. TOTP (authenticator apps) + recovery
MFA_SUPPORTED_TYPES = ["totp", "recovery_codes"]
MFA_TOTP_ISSUER = "Depot Management"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",  # switch to DEBUG to see all SQL queries
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
