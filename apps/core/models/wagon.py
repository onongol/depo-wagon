from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.constants import RepairType, WagonStatus, WagonType


def current_year() -> int:
    return timezone.now().year


class Wagon(models.Model):
    """Model representing a wagon in the depot."""

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
        blank=True,
        default="",
        verbose_name=_("Repair Type"),
    )
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Wagon")
        verbose_name_plural = _("Wagons")
        ordering = ["number"]
        indexes = [
            models.Index(fields=["status", "wagon_type"]),
            models.Index(fields=["status", "last_repair_date"]),
            models.Index(fields=["status", "next_repair_date"]),
        ]

    def __str__(self) -> str:
        return f"{_('Wagon')}: {self.number}"

    def save(self, *args, **kwargs) -> None:
        """Run full model validation before every save.

        NOTE: adds an extra SELECT (validate_unique) per call and triggers
        double validation in forms/Admin. For bulk imports use
        Wagon.objects.bulk_create(wagons) which bypasses save().
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """Validate repair dates are logically consistent with manufacture year."""
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
    def needs_repair_soon(self) -> bool:
        """Check if the wagon's next repair date is within the warning period."""
        if not self.next_repair_date:
            return False
        days = getattr(settings, "REPAIR_WARNING_DAYS", 30)
        return self.next_repair_date <= timezone.now().date() + timedelta(days=days)
