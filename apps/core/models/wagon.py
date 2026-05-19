from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.constants import RepairType, WagonStatus, WagonType


def current_year():
    return timezone.now().year


class Wagon(models.Model):
    number = models.CharField(
        max_length=20, unique=True, verbose_name=_("Wagon Number")
    )
    wagon_type = models.CharField(
        max_length=20, choices=WagonType.choices, verbose_name=_("Wagon Type")
    )
    manufacture_year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(current_year)],
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

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.last_repair_date and self.last_repair_date.year < self.manufacture_year:
            raise ValidationError(
                {
                    "last_repair_date": _(
                        "Last repair date cannot be earlier than the manufacture year."
                    )
                }
            )

        if self.last_repair_date and self.next_repair_date:
            if self.next_repair_date <= self.last_repair_date:
                raise ValidationError(
                    {
                        "next_repair_date": _(
                            "Next repair date must be later than the last repair date."
                        )
                    }
                )

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
        ordering = ["number"]
        indexes = [
            models.Index(fields=["status", "wagon_type"]),
            models.Index(fields=["status", "last_repair_date"]),
            models.Index(fields=["status", "next_repair_date"]),
        ]
