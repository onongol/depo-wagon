import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from apps.core.constants import EmployeeRole
from apps.users.adapters import AccountAdapter

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    """allauth's rate limits live in the cache; leaking them across tests would
    make later logins fail for reasons the test never set up."""
    cache.clear()
    yield


@pytest.fixture
def employee_user(db):
    user = User.objects.create_user(email="forms@depot.mn", password="pass12345")
    baker.make("core.Employee", user=user, role=EmployeeRole.INSPECTOR)
    EmailAddress.objects.create(
        user=user, email=user.email, verified=True, primary=True
    )
    return user


class TestPasswordPolicy:
    """Read from the base settings module rather than the ``settings`` fixture:
    config.settings.test empties AUTH_PASSWORD_VALIDATORS so the breach check
    doesn't call out to the network on every password a test sets."""

    def test_the_minimum_length_is_raised_above_djangos_default(self):
        from config.settings import base

        lengths = [
            v.get("OPTIONS", {}).get("min_length")
            for v in base.AUTH_PASSWORD_VALIDATORS
            if v["NAME"].endswith("MinimumLengthValidator")
        ]
        assert lengths == [12]

    def test_a_breach_check_is_actually_configured(self):
        from config.settings import base

        names = [v["NAME"] for v in base.AUTH_PASSWORD_VALIDATORS]
        assert any("Pwned" in name for name in names)


@pytest.mark.django_db
class TestStandardFormsAreUsed:
    def test_no_form_classes_are_overridden(self, settings):
        """The app styles allauth through templates, not form subclasses. A new
        ACCOUNT_FORMS entry means that decision was reversed somewhere."""
        assert getattr(settings, "ACCOUNT_FORMS", {}) == {}

    def test_signup_still_enforces_the_employee_gate(self, client):
        """The one form class the project does supply, and the reason it exists."""
        r = client.post(
            reverse("account_signup"),
            {
                "email": "stranger@example.com",
                "password1": "correct-horse-battery",
                "password2": "correct-horse-battery",
            },
        )
        assert r.status_code == 200
        assert not User.objects.filter(email="stranger@example.com").exists()


@pytest.mark.django_db
class TestReauthenticationMethods:
    def test_password_is_offered_when_there_is_no_second_factor(self, employee_user):
        methods = AccountAdapter().get_reauthentication_methods(employee_user)
        assert {m["id"] for m in methods} == {"reauthenticate"}

    def test_only_mfa_is_offered_once_a_second_factor_exists(self, employee_user):
        from allauth.mfa.models import Authenticator
        from allauth.mfa.totp.internal import auth as totp_auth

        totp_auth.TOTP.activate(employee_user, totp_auth.generate_totp_secret())
        assert Authenticator.objects.filter(user=employee_user).exists()

        methods = AccountAdapter().get_reauthentication_methods(employee_user)
        assert {m["id"] for m in methods} == {"mfa_reauthenticate"}


@pytest.mark.django_db
class TestPasswordChangeFlow:
    def test_changing_the_password_signs_every_session_out(
        self, client, employee_user, mailoutbox
    ):
        """ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE, end to end. Someone changing their
        password because they think it leaked expects the leak to stop working
        everywhere, not just to be asked for a new one here."""
        client.force_login(employee_user)
        new_password = "quiet-depot-lantern-42"

        r = client.post(
            reverse("account_change_password"),
            {
                "oldpassword": "pass12345",
                "password1": new_password,
                "password2": new_password,
            },
        )
        assert r.status_code == 302

        employee_user.refresh_from_db()
        assert employee_user.check_password(new_password)
        assert not client.session.get("_auth_user_id")

        # ACCOUNT_EMAIL_NOTIFICATIONS: the account holder is told, so a change
        # made from a stolen session does not pass unnoticed.
        assert len(mailoutbox) == 1
        assert employee_user.email in mailoutbox[0].to

    def test_the_old_password_is_required(self, client, employee_user):
        client.force_login(employee_user)
        r = client.post(
            reverse("account_change_password"),
            {
                "oldpassword": "not-the-current-one",
                "password1": "quiet-depot-lantern-42",
                "password2": "quiet-depot-lantern-42",
            },
        )
        assert r.status_code == 200
        employee_user.refresh_from_db()
        assert employee_user.check_password("pass12345")


@pytest.mark.django_db
class TestSecuritySettings:
    """Settings whose value is the whole point — a silent flip to the default
    would weaken sign-in without breaking anything visible."""

    def test_email_is_the_only_login_identifier(self, settings):
        assert sorted(settings.ACCOUNT_LOGIN_METHODS) == ["email"]
        assert settings.ACCOUNT_USER_MODEL_USERNAME_FIELD is None

    def test_verification_is_mandatory(self, settings):
        assert settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory"

    def test_logout_needs_a_post(self, settings):
        assert settings.ACCOUNT_LOGOUT_ON_GET is False

    def test_failed_logins_are_rate_limited(self, settings):
        assert "login_failed" in settings.ACCOUNT_RATE_LIMITS

    def test_account_changes_are_mailed_to_the_owner(self, settings):
        assert settings.ACCOUNT_EMAIL_NOTIFICATIONS is True
