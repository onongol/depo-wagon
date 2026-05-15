from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.constants import EmployeeRole


class Employee(models.Model):
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

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.employee_id})"

    class Meta:
        verbose_name = _("Employee")
        verbose_name_plural = _("Employees")
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["first_name", "last_name"]),
        ]
