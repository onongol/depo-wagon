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


@pytest.fixture
def user(db):
    return User.objects.create_user(email=EMAIL, password=PASSWORD)


def api_login(client, password=PASSWORD):
    return client.post(
        reverse("knox-login"),
        {"email": EMAIL, "password": password},
        format="json",
    )


@pytest.mark.django_db
def test_failed_attempts_are_throttled(user):
    client = APIClient()
    for _ in range(PER_ACCOUNT_FAILURES):
        assert api_login(client, "wrong").status_code == status.HTTP_400_BAD_REQUEST

    assert api_login(client, "wrong").status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
def test_the_budget_is_shared_with_the_web_form(client, user):
    """Both endpoints authenticate through allauth's adapter, so attempts add up.

    Counting them separately would leave this one — no CSRF token, no HTML —
    as an unmetered way to brute-force the accounts the web form protects.
    """
    for _ in range(PER_ACCOUNT_FAILURES):
        client.post(reverse("account_login"), {"login": EMAIL, "password": "wrong"})

    assert api_login(APIClient()).status_code == status.HTTP_429_TOO_MANY_REQUESTS
