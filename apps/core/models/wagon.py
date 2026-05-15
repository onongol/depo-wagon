from datetime import date, timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.constants import RepairType, WagonStatus, WagonType


class Wagon(models.Model):
    number = models.CharField(
        max_length=20, unique=True, verbose_name=_("Wagon Number")
    )
    wagon_type = models.CharField(
        max_length=20, choices=WagonType.choices, verbose_name=_("Wagon Type")
    )
    manufacture_year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1900)],
        verbose_name=_("Manufacture Year"),
    )
    last_repair_date = models.DateField(
        null=True, blank=True, verbose_name=_("Last Repair Date")
    )
    next_repair_date = models.DateField(
        null=True, blank=True, verbose_name=_("Next Repair Date")
    )
    mileage_km = models.PositiveIntegerField(default=0, verbose_name=_("Mileage (km)"))
    owner = models.CharField(max_length=200, blank=True, verbose_name=_("Owner"))
    status = models.CharField(
        max_length=20,
        choices=WagonStatus.choices,
        default=WagonStatus.ACTIVE,
        verbose_name=_("Status"),
    )
    repair_type = models.CharField(
        max_length=20,
        choices=RepairType.choices,
        null=True,
        blank=True,
        verbose_name=_("Repair Type"),
    )
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    history = HistoricalRecords()

    @property
    def needs_repair_soon(self):
        """Check if the wagon's next repair date is within the warning period."""
        if not self.next_repair_date:
            return False
        days = getattr(settings, "REPAIR_WARNING_DAYS", 30)
        return self.next_repair_date <= date.today() + timedelta(days=days)

    def __str__(self):
        return f"{_('Wagon')}: {self.number}"

    class Meta:
        verbose_name = _("Wagon")
        verbose_name_plural = _("Wagons")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["wagon_type"]),
            models.Index(fields=["last_repair_date"]),
            models.Index(fields=["next_repair_date"]),
        ]
