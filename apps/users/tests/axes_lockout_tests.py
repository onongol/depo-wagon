import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.users.axes import get_username

User = get_user_model()

ADMIN_EMAIL = "admin@depot.mn"
PASSWORD = "pass123"
ADMIN_LOGIN_URL = "/admin/login/"


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email=ADMIN_EMAIL, password=PASSWORD)


def admin_login(client, password=PASSWORD):
    return client.post(
        ADMIN_LOGIN_URL,
        {"username": ADMIN_EMAIL, "password": password, "next": "/admin/"},
    )


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "Admin@Depot.mn"},  # allauth and the API
        {
            "username": "Admin@Depot.mn"
        },  # Django's admin form, whatever USERNAME_FIELD is
    ],
)
def test_the_attempted_account_is_read_from_either_credential_shape(credentials):
    """A lockout keyed on None matches no account, so it stops refusing one."""
    assert get_username(None, credentials) == ADMIN_EMAIL


@pytest.mark.django_db
def test_the_admin_login_locks_out(client, admin_user):
    """allauth's limiter never sees /admin/: its form calls authenticate()
    directly, never the adapter that counts attempts. Axes is what covers it."""
    for _ in range(settings.AXES_FAILURE_LIMIT):
        admin_login(client, "wrong")

    assert admin_login(client, "wrong").status_code == 429


@pytest.mark.django_db
def test_the_lockout_holds_against_the_right_password(client, admin_user):
    for _ in range(settings.AXES_FAILURE_LIMIT):
        admin_login(client, "wrong")

    r = admin_login(client)
    assert r.status_code == 429
    assert not r.wsgi_request.user.is_authenticated
