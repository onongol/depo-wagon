"""Every allauth page this app exposes must render.

The project supplies only ``templates/allauth/layouts/``, which those pages
inherit; a typo there breaks them at render time, not at startup.
"""

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from apps.core.constants import EmployeeRole

User = get_user_model()

# Reachable while signed out.
ENTRANCE_PAGES = [
    "account_login",
    "account_signup",
    "account_reset_password",
    "account_reset_password_done",
]

# Reachable while signed in. Some of these redirect into a reauthentication
# flow rather than rendering, which is a pass — the point is that nothing 500s.
MANAGE_PAGES = [
    "account_email",
    "account_change_password",
    "account_logout",
    "mfa_index",
    "mfa_activate_totp",
    "usersessions_list",
]


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield


@pytest.fixture
def signed_in_client(client, db):
    user = User.objects.create_user(email="pages@depot.mn", password="pass12345")
    baker.make("core.Employee", user=user, role=EmployeeRole.INSPECTOR)
    EmailAddress.objects.create(
        user=user, email=user.email, verified=True, primary=True
    )
    client.force_login(user)
    return client


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", ENTRANCE_PAGES)
def test_entrance_pages_render(client, url_name):
    r = client.get(reverse(url_name))
    assert r.status_code == 200, url_name


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", MANAGE_PAGES)
def test_manage_pages_render(signed_in_client, url_name):
    r = signed_in_client.get(reverse(url_name))
    assert r.status_code in (200, 302), url_name


@pytest.mark.django_db
def test_entrance_pages_do_not_show_the_app_shell(client):
    """The sign-in pages use their own layout: a navbar and sidebar rendered
    around a login form are navigation for people who are already inside."""
    body = client.get(reverse("account_login")).content.decode()
    assert "Sidebar navigation" not in body


@pytest.mark.django_db
def test_manage_pages_keep_the_app_shell(signed_in_client):
    body = signed_in_client.get(reverse("account_change_password")).content.decode()
    assert "Sidebar navigation" in body


@pytest.mark.django_db
def test_the_login_page_offers_a_way_to_reset_a_password(client):
    """allauth's login template has no reset link of its own — the only one is
    inside the password field's help text, which the field partial has to
    render or the page becomes a dead end for anyone who forgot their password."""
    body = client.get(reverse("account_login")).content.decode()
    assert reverse("account_reset_password") in body


@pytest.mark.django_db
def test_password_rules_reach_the_page_they_describe(client, settings):
    """The signup input is marked `aria-describedby="id_password1_helptext"` by
    Django itself; if the partial drops help text, that points at nothing."""
    settings.AUTH_PASSWORD_VALIDATORS = [
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
            "OPTIONS": {"min_length": 12},
        },
    ]
    body = client.get(reverse("account_signup")).content.decode()
    assert 'aria-describedby="id_password1_helptext"' in body
    assert 'id="id_password1_helptext"' in body
    assert "at least 12 characters" in body
