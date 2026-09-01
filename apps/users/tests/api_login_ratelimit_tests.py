import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

EMAIL = "throttled@depot.mn"
PASSWORD = "pass123"

# ACCOUNT_RATE_LIMITS["login_failed"], the 5/300s/key part.
PER_ACCOUNT_FAILURES = 5

LOGIN_URL = reverse("headless:app:account:login")


@pytest.fixture
def user(db):
    return User.objects.create_user(email=EMAIL, password=PASSWORD)


def api_login(client, password=PASSWORD):
    return client.post(
        LOGIN_URL,
        {"email": EMAIL, "password": password},
        format="json",
    )


def error_codes(response):
    """Headless reports a spent budget as a 400 error code, not as a 429."""
    return {error["code"] for error in response.json().get("errors", [])}


@pytest.mark.django_db
def test_failed_attempts_are_throttled(user):
    client = APIClient()
    for _ in range(PER_ACCOUNT_FAILURES):
        response = api_login(client, "wrong")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert error_codes(response) == {"email_password_mismatch"}

    assert error_codes(api_login(client, "wrong")) == {"too_many_login_attempts"}


@pytest.mark.django_db
def test_the_budget_is_shared_with_the_web_form(client, user):
    """Both endpoints authenticate through allauth, so attempts add up.

    Counting them separately would leave this one — no CSRF token, no HTML —
    as an unmetered way to brute-force the accounts the web form protects.
    """
    for _ in range(PER_ACCOUNT_FAILURES):
        client.post(reverse("account_login"), {"login": EMAIL, "password": "wrong"})

    assert error_codes(api_login(APIClient())) == {"too_many_login_attempts"}
