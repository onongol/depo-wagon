from config.settings.base import *

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = False

# DATABASES
# ------------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "test_db",
        "USER": "test_user",
        "PASSWORD": "test_pass",
        "HOST": "localhost",
        "PORT": 5433,
    }
}

# CACHES
# ------------------------------------------------------------------------------
# Local memory, so rate limits and one-time tokens don't leak between runs via Redis.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "depo-wagon-tests",
    }
}

# CELERY
# ------------------------------------------------------------------------------
# In-memory transport: .delay() in a test would otherwise publish a real task
# into whatever Redis the developer has running.
CELERY_BROKER_URL = "memory://"

# PASSWORDS
# ------------------------------------------------------------------------------
# Faster password hashing in tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = []

# MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = [*MIDDLEWARE, AXES_MIDDLEWARE_PATH]
assert MIDDLEWARE[-1] == AXES_MIDDLEWARE_PATH, "AxesMiddleware must be last"

# STATIC
# ------------------------------------------------------------------------------
STATICFILES_DIRS = []
STATIC_ROOT = None

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# EMAIL
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
EMAIL_DELIVERY_BACKEND = EMAIL_BACKEND

# LOGGING
# ------------------------------------------------------------------------------
# Disable logging in tests
LOGGING = {}
