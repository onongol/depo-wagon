"""The production module is never loaded by the suite, so its own logic is
untested unless read directly. Only the two settings it computes are covered
here; the literal ones are `manage.py check --deploy`'s job."""

import importlib

import pytest


def load_production(monkeypatch, **env):
    env.setdefault("ALLOWED_HOSTS", "depowagon.mn")
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


@pytest.mark.parametrize(
    ("hosts", "expected"),
    [
        (
            "depowagon.mn,www.depowagon.mn",
            ["https://depowagon.mn", "https://www.depowagon.mn"],
        ),
        # Django wants https://*.example.com, not https://.example.com.
        (".depowagon.mn", ["https://*.depowagon.mn"]),
    ],
)
def test_csrf_origins_are_derived_from_the_allowed_hosts(monkeypatch, hosts, expected):
    origins = load_production(monkeypatch, ALLOWED_HOSTS=hosts).CSRF_TRUSTED_ORIGINS

    assert origins == expected
