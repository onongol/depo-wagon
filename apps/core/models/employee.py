from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.constants import Department, EmployeeRole


class Employee(models.Model):
    """Model representing an employee."""

    employee_id = models.CharField(
        max_length=20, unique=True, verbose_name=_("Employee ID")
    )
    first_name = models.CharField(max_length=100, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=100, verbose_name=_("Last Name"))
    role = models.CharField(
        max_length=20,
        choices=EmployeeRole.choices,
        verbose_name=_("Role"),
    )
    department = models.CharField(
        max_length=20,
        choices=Department.choices,
        blank=True,
        verbose_name=_("Department"),
    )
    telegram_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        verbose_name=_("Telegram ID"),
    )
    user = models.OneToOneField(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee",
        verbose_name=_("User"),
    )
    phone = models.CharField(
        max_length=20, unique=True, null=True, blank=True, verbose_name=_("Phone")
    )
    email = models.EmailField(
        unique=True, null=True, blank=True, verbose_name=_("Email")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    history = HistoricalRecords()

    def save(self, *args, **kwargs) -> None:
        """Override save to ensure phone and email are set to None if blank, and to sync user active status."""
        self.phone = self.phone or None
        self.email = self.email or None
        super().save(*args, **kwargs)

        if self.user_id:
            get_user_model().objects.filter(pk=self.user_id).update(
                is_active=self.is_active
            )

    class Meta:
        verbose_name = _("Employee")
        verbose_name_plural = _("Employees")
        ordering = ["employee_id"]
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["first_name"]),
            models.Index(fields=["last_name"]),
            models.Index(fields=["department"]),
        ]

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name}"

    @property
    def short_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.last_name[0]}.{self.first_name}"
        return self.first_name or self.last_name or self.employee_id

    def __str__(self) -> str:
        return f"{self.full_name} ({self.employee_id})"
