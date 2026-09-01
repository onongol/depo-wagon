import pytest
from allauth.account.models import EmailAddress
from allauth.mfa.totp.internal import auth as totp_auth
from django.contrib.auth import get_user_model
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.constants import EmployeeRole

User = get_user_model()

TEST_EMAIL = "test@depot.mn"
TEST_PASSWORD = "pass123"

LOGIN_URL = reverse("headless:app:account:login")
SESSION_URL = reverse("headless:app:account:current_session")
REFRESH_URL = reverse("headless:app:tokens:refresh")


def verify_email(user):
    EmailAddress.objects.update_or_create(
        user=user, email=user.email, defaults={"verified": True, "primary": True}
    )


@pytest.fixture
def user(db):
    user = User.objects.create_user(email=TEST_EMAIL, password=TEST_PASSWORD)
    baker.make("core.Employee", user=user, role=EmployeeRole.INSPECTOR)
    verify_email(user)
    return user


@pytest.fixture
def api_client():
    return APIClient()


def login(client, email=TEST_EMAIL, password=TEST_PASSWORD):
    return client.post(LOGIN_URL, {"email": email, "password": password}, format="json")


@pytest.fixture
def auth_client(user):
    response = login(APIClient())
    assert response.status_code == status.HTTP_200_OK, (
        f"Login failed in fixture: {response.status_code} {response.json()}"
    )
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {response.json()['meta']['access_token']}"
    )
    return client


@pytest.mark.django_db
class TestLogin:
    def test_login_returns_200(self, api_client, user):
        assert login(api_client).status_code == status.HTTP_200_OK

    def test_login_returns_an_access_and_refresh_token(self, api_client, user):
        meta = login(api_client).json()["meta"]
        assert meta["access_token"]
        assert meta["refresh_token"]

    def test_login_reports_the_user(self, api_client, user):
        response = login(api_client)
        assert response.json()["data"]["user"]["email"] == TEST_EMAIL

    def test_login_wrong_password_returns_400(self, api_client, user):
        assert login(api_client, password="wrongpass").status_code == (
            status.HTTP_400_BAD_REQUEST
        )

    def test_login_wrong_email_returns_400(self, api_client, user):
        assert login(api_client, email="wrong@depot.mn").status_code == (
            status.HTTP_400_BAD_REQUEST
        )

    def test_login_missing_fields_returns_400(self, api_client):
        response = api_client.post(LOGIN_URL, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user_is_refused(self, api_client, user):
        user.is_active = False
        user.save()

        response = login(api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["meta"]["is_authenticated"] is False


@pytest.mark.django_db
class TestLoginStages:
    """Login stops at a pending stage, and issues no access token until it clears."""

    def test_unverified_email_is_refused(self, api_client, db):
        user = User.objects.create_user(email=TEST_EMAIL, password=TEST_PASSWORD)
        baker.make("core.Employee", user=user, role=EmployeeRole.INSPECTOR)

        response = login(api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        pending = {
            f["id"] for f in response.json()["data"]["flows"] if f.get("is_pending")
        }
        assert pending == {"verify_email"}

    def test_mfa_is_required_before_a_token_is_usable(self, api_client, user):
        totp_auth.TOTP.activate(user, totp_auth.generate_totp_secret())

        response = login(api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        pending = {
            f["id"] for f in response.json()["data"]["flows"] if f.get("is_pending")
        }
        assert pending == {"mfa_authenticate"}

    def test_no_access_token_is_issued_while_a_stage_is_pending(self, api_client, user):
        totp_auth.TOTP.activate(user, totp_auth.generate_totp_secret())

        meta = login(api_client).json()["meta"]

        assert meta["session_token"]
        assert "access_token" not in meta


@pytest.mark.django_db
class TestLogout:
    def test_logout_returns_401_with_an_anonymous_session(self, auth_client):
        response = auth_client.delete(SESSION_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["meta"]["is_authenticated"] is False

    def test_logout_invalidates_the_token(self, auth_client):
        auth_client.delete(SESSION_URL)
        response = auth_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_without_a_token_returns_401(self, api_client):
        assert api_client.delete(SESSION_URL).status_code == (
            status.HTTP_401_UNAUTHORIZED
        )


@pytest.mark.django_db
class TestRefresh:
    def test_refresh_returns_a_usable_access_token(self, api_client, user):
        refresh_token = login(api_client).json()["meta"]["refresh_token"]

        response = api_client.post(
            REFRESH_URL, {"refresh_token": refresh_token}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.json()['data']['access_token']}"
        )
        assert client.get(reverse("wagon-list")).status_code == status.HTTP_200_OK

    def test_refresh_rotates_the_refresh_token(self, api_client, user):
        refresh_token = login(api_client).json()["meta"]["refresh_token"]

        response = api_client.post(
            REFRESH_URL, {"refresh_token": refresh_token}, format="json"
        )

        assert response.json()["data"]["refresh_token"] != refresh_token

    def test_an_unknown_refresh_token_is_rejected(self, api_client):
        response = api_client.post(
            REFRESH_URL, {"refresh_token": "nonsense"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestProtectedEndpoints:
    def test_wagons_without_token_returns_401(self, api_client):
        response = api_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_wagons_with_token_returns_200(self, auth_client):
        response = auth_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_defects_without_token_returns_401(self, api_client):
        response = api_client.get(reverse("defect-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_defects_with_token_returns_200(self, auth_client):
        response = auth_client.get(reverse("defect-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_token_returns_401(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalidtoken123")
        response = api_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
