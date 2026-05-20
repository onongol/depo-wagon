import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestCustomUserManager:
    def test_create_user(self):
        user = User.objects.create_user(email="test@example.com", password="pass123")
        assert user.email == "test@example.com"
        assert user.check_password("pass123")
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(email="Test@EXAMPLE.COM", password="pass123")
        assert user.email == "Test@example.com"  # only domain is lowercased

    def test_create_user_without_email_raises(self):
        with pytest.raises(ValueError, match="Email is required"):
            User.objects.create_user(email="", password="pass123")

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@example.com", password="pass123"
        )
        assert user.is_staff
        assert user.is_superuser

    def test_create_superuser_without_is_staff_raises(self):
        with pytest.raises(ValueError, match="is_staff=True"):
            User.objects.create_superuser(
                email="admin@example.com", password="pass123", is_staff=False
            )

    def test_create_superuser_without_is_superuser_raises(self):
        with pytest.raises(ValueError, match="is_superuser=True"):
            User.objects.create_superuser(
                email="admin@example.com", password="pass123", is_superuser=False
            )


@pytest.mark.django_db
class TestCustomUser:
    def test_email_is_unique(self):
        User.objects.create_user(email="unique@example.com", password="pass123")
        with pytest.raises(Exception):
            User.objects.create_user(email="unique@example.com", password="pass456")

    def test_username_field_is_email(self):
        assert User.USERNAME_FIELD == "email"

    def test_required_fields_empty(self):
        assert User.REQUIRED_FIELDS == []

    def test_user_is_active_by_default(self):
        user = User.objects.create_user(email="active@example.com", password="pass123")
        assert user.is_active
