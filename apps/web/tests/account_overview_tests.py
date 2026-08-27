import pytest
from allauth.account.models import EmailAddress
from allauth.usersessions.models import UserSession
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from apps.core.constants import EmployeeRole

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield


def _make_user(email="acct@depot.mn", with_employee=True):
    user = User.objects.create_user(email=email, password="pass12345")
    EmailAddress.objects.create(
        user=user, email=user.email, verified=True, primary=True
    )
    if with_employee:
        baker.make(
            "core.Employee",
            user=user,
            role=EmployeeRole.INSPECTOR,
            is_active=True,
        )
    return user


def _sign_in(user, using=None):
    """Sign `user` in and make one request, so the middleware records the session.

    Returns the ``UserSession`` that request created. Pass `using` to reuse a
    client; omit it to get a fresh one, standing in for a second device.
    """
    from django.test import Client

    client = using or Client()
    before = set(UserSession.objects.filter(user=user).values_list("pk", flat=True))
    client.force_login(user)
    client.get(reverse("web:account_overview"))
    created = UserSession.objects.filter(user=user).exclude(pk__in=before)
    return created.get()


@pytest.mark.django_db
class TestAccountOverview:
    def test_requires_login(self, client):
        r = client.get(reverse("web:account_overview"))
        assert r.status_code == 302
        assert "/accounts/login/" in r.url

    def test_links_to_every_allauth_page(self, client):
        """The point of the page: none of these URLs is reachable without it."""
        client.force_login(_make_user())
        r = client.get(reverse("web:account_overview"))
        assert r.status_code == 200
        body = r.content.decode()
        for name in (
            "account_email",
            "account_change_password",
            "mfa_index",
            "usersessions_list",
        ):
            assert reverse(name) in body, name

    def test_reports_mfa_as_off_when_not_set_up(self, client):
        client.force_login(_make_user())
        r = client.get(reverse("web:account_overview"))
        assert r.context["is_mfa_enabled"] is False

    def test_renders_without_an_employee_record(self, client):
        """A superuser from `createsuperuser` has no HR record and must not 500."""
        client.force_login(_make_user(email="root@depot.mn", with_employee=False))
        r = client.get(reverse("web:account_overview"))
        assert r.status_code == 200
        assert r.context["employee"] is None

    def test_counts_signed_in_devices(self, client):
        user = _make_user()
        _sign_in(user, using=client)
        _sign_in(user)
        r = client.get(reverse("web:account_overview"))
        assert r.context["session_count"] == 2


@pytest.mark.django_db
class TestSessionListPage:
    """The project replaces allauth's own template for this page — see
    templates/usersessions/usersession_list.html for why."""

    def test_offers_a_sign_out_button_per_other_device(self, client):
        user = _make_user()
        elsewhere = _sign_in(user)
        _sign_in(user, using=client)

        r = client.get(reverse("usersessions_list"))
        assert r.status_code == 200
        body = r.content.decode()
        assert reverse("web:end_user_session", args=[elsewhere.pk]) in body

    def test_the_current_device_gets_no_sign_out_button(self, client):
        user = _make_user()
        current = _sign_in(user, using=client)

        r = client.get(reverse("usersessions_list"))
        body = r.content.decode()
        assert reverse("web:end_user_session", args=[current.pk]) not in body
        assert "This device" in body


@pytest.mark.django_db
class TestEndUserSession:
    def test_rejects_get(self, client):
        user = _make_user()
        session = _sign_in(user, using=client)
        r = client.get(reverse("web:end_user_session", args=[session.pk]))
        assert r.status_code == 405
        assert UserSession.objects.filter(pk=session.pk).exists()

    def test_cannot_end_another_users_session(self, client):
        victim = _make_user(email="victim@depot.mn")
        victims_session = _sign_in(victim)

        _sign_in(_make_user(email="attacker@depot.mn"), using=client)

        r = client.post(reverse("web:end_user_session", args=[victims_session.pk]))
        assert r.status_code == 404
        assert UserSession.objects.filter(pk=victims_session.pk).exists()

    def test_ending_the_current_session_is_a_no_op(self, client):
        """Otherwise the button on the "this device" row would sign you out."""
        user = _make_user()
        session = _sign_in(user, using=client)

        r = client.post(reverse("web:end_user_session", args=[session.pk]))
        assert r.status_code == 302
        assert UserSession.objects.filter(pk=session.pk).exists()

    def test_ends_another_device(self, client):
        user = _make_user()
        elsewhere = _sign_in(user)
        _sign_in(user, using=client)

        r = client.post(reverse("web:end_user_session", args=[elsewhere.pk]))
        assert r.status_code == 302
        assert r.url == reverse("web:account_overview")
        assert not UserSession.objects.filter(pk=elsewhere.pk).exists()
