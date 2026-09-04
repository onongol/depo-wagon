from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """User manager keyed on email instead of username."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("Email is required"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        user = self.create_user(email, password, **extra_fields)

        # Email verification is mandatory, so an account with no verified
        # address cannot sign in to the web app at all. `createsuperuser` runs
        # on the server by someone who already has shell access, so requiring
        # them to confirm their own address adds nothing — without this they'd
        # be silently limited to /admin/ and stuck on the confirmation page
        # everywhere else.
        from allauth.account.models import EmailAddress

        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"verified": True, "primary": True},
        )
        return user


class CustomUser(AbstractUser):
    """Custom user model that uses email instead of username."""

    objects = CustomUserManager()
    username = None
    email = models.EmailField(unique=True, verbose_name=_("Email"))

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
