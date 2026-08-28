"""The production module is never loaded by the suite, so its own logic is
untested unless read directly. Only what it computes or refuses is covered
here; the literal settings are `manage.py check --deploy`'s job."""

import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured


def load_production(monkeypatch, **env):
    env.setdefault("ALLOWED_HOSTS", "depowagon.mn")
    env.setdefault("CSRF_TRUSTED_ORIGINS", "https://depowagon.mn")
    env.setdefault("DJANGO_ADMIN_URL", "admin/")
    env.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
    env.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
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
