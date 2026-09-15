from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.mixins import UpdatedAtMixin
from apps.defects.constants import MeasurementDimension


class DefectMeasurement(UpdatedAtMixin, models.Model):
    """Model representing a measurement associated with a defect."""

    defect = models.ForeignKey(
        "defects.Defect",
        on_delete=models.CASCADE,
        db_index=False,
        related_name="measurements",
        verbose_name=_("Defect"),
    )
    dimension = models.CharField(
        max_length=20,
        choices=MeasurementDimension.choices,
        verbose_name=_("Dimension"),
    )
    value = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Value")
    )
    norm_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Norm Value"),
    )
    unit = models.CharField(max_length=20, blank=True, verbose_name=_("Unit"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Measurement")
        verbose_name_plural = _("Measurements")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["defect", "dimension"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        unit_str = f" {self.unit}" if self.unit else ""
        return f"{self.get_dimension_display()}: {self.value}{unit_str}"

    @property
    def is_exceeded(self) -> bool:
        if self.norm_value is not None:
            return self.value > self.norm_value
        return False
