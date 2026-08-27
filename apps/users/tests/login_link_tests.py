import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from apps.core.constants import EmployeeRole
from apps.users import login_tokens

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield


@pytest.fixture
def employee_user(db):
    from allauth.account.models import EmailAddress

    user = User.objects.create_user(email="link@depot.mn", password=None)
    baker.make("core.Employee", user=user, role=EmployeeRole.INSPECTOR)
    EmailAddress.objects.create(
        user=user, email=user.email, verified=True, primary=True
    )
    return user


class TestIssueAndRedeem:
    def test_redeem_returns_the_user_id(self):
        token = login_tokens.issue(42)
        assert login_tokens.redeem(token) == 42

    def test_token_works_only_once(self):
        token = login_tokens.issue(42)
        login_tokens.redeem(token)
        assert login_tokens.redeem(token) is None

    def test_unknown_token_returns_none(self):
        assert login_tokens.redeem("never-issued") is None

    def test_empty_token_returns_none(self):
        assert login_tokens.redeem("") is None

    def test_two_tokens_are_distinct(self):
        assert login_tokens.issue(1) != login_tokens.issue(1)


@pytest.mark.django_db
class TestLoginLinkView:
    def test_valid_link_signs_the_user_in(self, client, employee_user):
        token = login_tokens.issue(employee_user.pk)
        r = client.get(reverse("login_link", kwargs={"token": token}))
        assert r.wsgi_request.user.is_authenticated, r.content[:500]

    def test_valid_link_signs_in_the_right_user(self, client, employee_user):
        token = login_tokens.issue(employee_user.pk)
        r = client.get(reverse("login_link", kwargs={"token": token}))
        assert r.wsgi_request.user.pk == employee_user.pk

    def test_link_cannot_be_replayed(self, client, employee_user):
        token = login_tokens.issue(employee_user.pk)
        url = reverse("login_link", kwargs={"token": token})
        client.get(url)
        client.logout()
        r = client.get(url)
        assert not r.wsgi_request.user.is_authenticated

    def test_expired_or_unknown_token_redirects_to_login(self, client):
        r = client.get(reverse("login_link", kwargs={"token": "bogus"}))
        assert r.status_code == 302
        assert reverse("account_login") in r.url

    def test_inactive_user_is_not_signed_in(self, client, employee_user):
        employee_user.is_active = False
        employee_user.save(update_fields=["is_active"])
        token = login_tokens.issue(employee_user.pk)
        r = client.get(reverse("login_link", kwargs={"token": token}))
        assert not r.wsgi_request.user.is_authenticated

    def test_post_is_not_allowed(self, client, employee_user):
        token = login_tokens.issue(employee_user.pk)
        r = client.post(reverse("login_link", kwargs={"token": token}))
        assert r.status_code == 405

    def test_signed_in_user_reaches_a_protected_page(self, client, employee_user):
        token = login_tokens.issue(employee_user.pk)
        client.get(reverse("login_link", kwargs={"token": token}))
        r = client.get(reverse("web:wagon_list"))
        assert r.status_code == 200
