from config.settings.base import *

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

# Local memory, so rate limits and one-time tokens don't leak between runs via Redis.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "depo-wagon-tests",
    }
}

MIDDLEWARE = [*MIDDLEWARE, AXES_MIDDLEWARE_PATH]
assert MIDDLEWARE[-1] == AXES_MIDDLEWARE_PATH, "AxesMiddleware must be last"

# Faster password hashing in tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# The real validator set calls the HaveIBeenPwned API, which would make every
# test that sets a password hit the network — slow, and failing offline. The
# validators themselves are exercised against the real settings module, not here.
AUTH_PASSWORD_VALIDATORS = []

# Keep mail in memory so tests can assert on django.core.mail.outbox instead of
# talking to Mailtrap.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable logging in tests
LOGGING = {}

STATICFILES_DIRS = []
STATIC_ROOT = None

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
