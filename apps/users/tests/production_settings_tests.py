"""The production module is never loaded by the suite, so its own logic is
untested unless read directly. Only what it computes or refuses is covered
here; the literal settings are `manage.py check --deploy`'s job."""

import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured


def load_production(monkeypatch, **env):
    # Every required variable, so a missing .env (as in CI) doesn't fail the import.
    env.setdefault("SECRET_KEY", "test-secret-key")
    env.setdefault("DATABASE_URL", "postgres://localhost:5432/depo_wagon")
    env.setdefault("REDIS_URL", "redis://localhost:6379/0")
    env.setdefault("ALLOWED_HOSTS", "depowagon.mn")
    env.setdefault("CSRF_TRUSTED_ORIGINS", "https://depowagon.mn")
    env.setdefault("DJANGO_ADMIN_URL", "admin/")
    env.setdefault("SITE_URL", "https://depowagon.mn")
    env.setdefault("DEFAULT_FROM_EMAIL", "noreply@example.com")
    env.setdefault("AWS_ACCESS_KEY_ID", "test")
    env.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    env.setdefault("AWS_STORAGE_BUCKET_NAME", "test")
    env.setdefault("AWS_S3_ENDPOINT_URL", "https://s3.example.com")
    env.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
    env.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    env.setdefault("TELEGRAM_BOT_TOKEN", "123:test")
    env.setdefault("TELEGRAM_FSM_REDIS_URL", "redis://localhost:6379/3")
    env.setdefault("GOOGLE_AI_KEY", "test")
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    from config.settings import production

    return importlib.reload(production)


@pytest.mark.parametrize(
    ("flag", "expected"),
    [
        ("true", ("HTTP_X_FORWARDED_PROTO", "https")),
        # A directly reachable gunicorn must not trust a header anyone can send.
        ("false", None),
    ],
)
def test_the_proxys_scheme_is_trusted_only_when_asked(monkeypatch, flag, expected):
    header = load_production(
        monkeypatch, USE_X_FORWARDED_PROTO=flag
    ).SECURE_PROXY_SSL_HEADER

    assert header == expected


@pytest.mark.parametrize("setting", ["ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS"])
def test_an_empty_host_list_is_refused(monkeypatch, setting):
    with pytest.raises(ImproperlyConfigured, match=setting):
        load_production(monkeypatch, **{setting: ""})


def test_an_unset_sender_address_is_refused(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="DEFAULT_FROM_EMAIL"):
        load_production(monkeypatch, DEFAULT_FROM_EMAIL="")


def test_an_unset_site_url_is_refused(monkeypatch):
    # The base default would send bot users and emails to localhost.
    with pytest.raises(ImproperlyConfigured, match="SITE_URL"):
        load_production(monkeypatch, SITE_URL="")


@pytest.mark.parametrize(
    ("setting", "value", "expected"),
    [
        (
            "ALLOWED_HOSTS",
            "depowagon.mn, www.depowagon.mn",
            ["depowagon.mn", "www.depowagon.mn"],
        ),
        # A leading space passes Django's 4_0.E001 scheme check and then never
        # matches an Origin header, so it has to be stripped here.
        (
            "CSRF_TRUSTED_ORIGINS",
            "https://depowagon.mn, https://www.depowagon.mn",
            ["https://depowagon.mn", "https://www.depowagon.mn"],
        ),
    ],
)
def test_whitespace_between_configured_values_is_stripped(
    monkeypatch, setting, value, expected
):
    production = load_production(monkeypatch, **{setting: value})

    assert getattr(production, setting) == expected
