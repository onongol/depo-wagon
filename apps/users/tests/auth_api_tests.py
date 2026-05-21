import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

TEST_EMAIL = "test@depot.mn"
TEST_PASSWORD = "pass123"


@pytest.fixture
def user(db):
    return User.objects.create_superuser(email=TEST_EMAIL, password=TEST_PASSWORD)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    response = client.post(
        reverse("knox-login"),
        {"email": TEST_EMAIL, "password": TEST_PASSWORD},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, (
        f"Login failed in fixture: {response.status_code} {response.data}"
    )
    client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
    return client


@pytest.mark.django_db
class TestLogin:
    def test_login_returns_200(self, api_client, user):
        response = api_client.post(
            reverse("knox-login"),
            {"email": TEST_EMAIL, "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_login_returns_token(self, api_client, user):
        response = api_client.post(
            reverse("knox-login"),
            {"email": TEST_EMAIL, "password": TEST_PASSWORD},
            format="json",
        )
        assert "token" in response.data
        assert response.data["token"] is not None

    def test_login_returns_expiry(self, api_client, user):
        response = api_client.post(
            reverse("knox-login"),
            {"email": TEST_EMAIL, "password": TEST_PASSWORD},
            format="json",
        )
        assert "expiry" in response.data

    def test_login_wrong_password_returns_400(self, api_client, user):
        response = api_client.post(
            reverse("knox-login"),
            {"email": TEST_EMAIL, "password": "wrongpass"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_wrong_email_returns_400(self, api_client, user):
        response = api_client.post(
            reverse("knox-login"),
            {"email": "wrong@depot.mn", "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_missing_fields_returns_400(self, api_client):
        response = api_client.post(reverse("knox-login"), {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user_returns_400(self, api_client, user):
        user.is_active = False
        user.save()
        response = api_client.post(
            reverse("knox-login"),
            {"email": TEST_EMAIL, "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogout:
    def test_logout_returns_204(self, auth_client):
        response = auth_client.post(reverse("knox-logout"))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_logout_invalidates_token(self, auth_client):
        auth_client.post(reverse("knox-logout"))
        response = auth_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_without_token_returns_401(self, api_client):
        response = api_client.post(reverse("knox-logout"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


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
        api_client.credentials(HTTP_AUTHORIZATION="Token invalidtoken123")
        response = api_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
