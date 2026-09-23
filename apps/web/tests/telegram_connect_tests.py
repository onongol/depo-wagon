import pytest
from aiogram.utils.deep_linking import BAD_PATTERN, DEEPLINK_PAYLOAD_LENGTH
from allauth.account.models import EmailAddress
from django.contrib.auth import SESSION_KEY, get_user_model
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from apps.core.constants import EmployeeRole
from apps.users import telegram_tokens

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield


def _make_employee_user(email="tg@depot.mn", telegram_id=None):
    user = User.objects.create_user(email=email, password="pass12345")
    employee = baker.make(
        "core.Employee",
        user=user,
        role=EmployeeRole.INSPECTOR,
        telegram_id=telegram_id,
        is_active=True,
    )
    EmailAddress.objects.create(
        user=user, email=user.email, verified=True, primary=True
    )
    return user, employee


@pytest.mark.django_db
class TestTelegramConnectPage:
    def test_requires_login(self, client):
        r = client.get(reverse("web:telegram_connect"))
        assert r.status_code == 302
        assert "/accounts/login/" in r.url

    def test_unlinked_employee_gets_a_deep_link(self, client, settings):
        settings.TELEGRAM_BOT_USERNAME = "depo_bot"
        user, _ = _make_employee_user()
        client.force_login(user)
        r = client.get(reverse("web:telegram_connect"))
        assert "https://t.me/depo_bot?start=" in r.context["deep_link"]

    def test_the_token_fits_a_telegram_deep_link(self, client, settings):
        """Telegram caps ?start= at 64 chars from [A-Za-z0-9_-]."""
        settings.TELEGRAM_BOT_USERNAME = "depo_bot"
        user, _ = _make_employee_user()
        client.force_login(user)
        r = client.get(reverse("web:telegram_connect"))
        token = r.context["deep_link"].split("start=")[1]

        assert len(token) <= DEEPLINK_PAYLOAD_LENGTH
        assert not BAD_PATTERN.search(token)

    def test_deep_link_token_is_redeemable_for_that_user(self, client, settings):
        settings.TELEGRAM_BOT_USERNAME = "depo_bot"
        user, _ = _make_employee_user()
        client.force_login(user)
        r = client.get(reverse("web:telegram_connect"))
        token = r.context["deep_link"].split("start=")[1]

        assert telegram_tokens.redeem(token) == user.pk

    def test_reloading_the_page_revokes_the_earlier_link(self, client, settings):
        settings.TELEGRAM_BOT_USERNAME = "depo_bot"
        user, _ = _make_employee_user()
        client.force_login(user)
        url = reverse("web:telegram_connect")
        stale = client.get(url).context["deep_link"].split("start=")[1]
        client.get(url)

        assert telegram_tokens.redeem(stale) is None

    def test_the_browser_is_told_not_to_keep_the_page(self, client, settings):
        settings.TELEGRAM_BOT_USERNAME = "depo_bot"
        user, _ = _make_employee_user()
        client.force_login(user)
        r = client.get(reverse("web:telegram_connect"))
        assert "no-store" in r["Cache-Control"]

    def test_linked_employee_is_offered_no_new_link(self, client, settings):
        settings.TELEGRAM_BOT_USERNAME = "depo_bot"
        user, _ = _make_employee_user(telegram_id=555)
        client.force_login(user)
        r = client.get(reverse("web:telegram_connect"))
        assert r.context["is_linked"]
        assert "deep_link" not in r.context or r.context["deep_link"] is None

    def test_page_degrades_when_bot_username_unset(self, client, settings):
        settings.TELEGRAM_BOT_USERNAME = ""
        user, _ = _make_employee_user()
        client.force_login(user)
        r = client.get(reverse("web:telegram_connect"))
        assert r.status_code == 200
        assert "deep_link" not in r.context or r.context["deep_link"] is None


@pytest.mark.django_db
class TestLinkDiesWithTheSession:
    """A link left on a shared screen must not work for whoever sits down next."""

    @pytest.fixture
    def token(self, client, settings):
        settings.TELEGRAM_BOT_USERNAME = "depo_bot"
        user, _ = _make_employee_user()
        client.force_login(user)
        r = client.get(reverse("web:telegram_connect"))
        return r.context["deep_link"].split("start=")[1]

    def test_logging_out_revokes_the_link(self, client, token):
        client.post(reverse("account_logout"))
        assert telegram_tokens.redeem(token) is None

    def test_changing_the_password_revokes_the_link(self, client, token):
        new_password = "Rail-depot-2026!"
        client.post(
            reverse("account_change_password"),
            {
                "oldpassword": "pass12345",
                "password1": new_password,
                "password2": new_password,
            },
        )
        assert User.objects.get(email="tg@depot.mn").check_password(new_password)
        assert telegram_tokens.redeem(token) is None

    def test_a_cache_outage_does_not_block_logout(self, client, token, monkeypatch):
        def cache_down(user_id):
            raise ConnectionError

        monkeypatch.setattr(telegram_tokens, "revoke", cache_down)
        client.post(reverse("account_logout"))
        assert SESSION_KEY not in client.session


@pytest.mark.django_db
class TestTelegramDisconnect:
    def test_post_clears_the_link(self, client):
        user, employee = _make_employee_user(telegram_id=555)
        client.force_login(user)
        client.post(reverse("web:telegram_disconnect"))
        employee.refresh_from_db()
        assert employee.telegram_id is None

    def test_the_owner_is_notified(self, client):
        from unittest.mock import patch

        user, _ = _make_employee_user(telegram_id=555)
        client.force_login(user)
        with patch("apps.web.views.telegram.notify_telegram_link_change") as notify:
            client.post(reverse("web:telegram_disconnect"))
        notify.assert_called_once_with(user, "disconnected")

    def test_get_is_rejected(self, client):
        user, employee = _make_employee_user(telegram_id=555)
        client.force_login(user)
        r = client.get(reverse("web:telegram_disconnect"))
        assert r.status_code == 405
        employee.refresh_from_db()
        assert employee.telegram_id == 555

    def test_requires_login(self, client):
        r = client.post(reverse("web:telegram_disconnect"))
        assert r.status_code == 302
