import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.constants import ROLES_WITH_ALL_DEFECTS, Department
from apps.defects.constants import (
    DefectNode,
    DefectSeverity,
    DefectStatus,
    DefectType,
    DefectVerdict,
)


class DefectQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Every defect for superusers, engineers and managers; others get their own."""
        if user.is_superuser:
            return self

        employee = getattr(user, "employee", None)
        if employee is None:
            return self.none()
        if employee.role in ROLES_WITH_ALL_DEFECTS:
            return self
        return self.filter(inspector=employee)


class Defect(models.Model):
    """Model representing a defect detected on a wagon."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wagon = models.ForeignKey(
        "core.Wagon",
        on_delete=models.CASCADE,
        related_name="defects",
        verbose_name=_("Wagon"),
    )
    department = models.CharField(
        max_length=20,
        choices=Department.choices,
        blank=True,
        verbose_name=_("Department"),
    )
    node = models.CharField(
        max_length=20, choices=DefectNode.choices, verbose_name=_("Node")
    )
    part_number = models.CharField(
        max_length=100, blank=True, verbose_name=_("Part Number")
    )
    defect_type = models.CharField(
        max_length=20, choices=DefectType.choices, verbose_name=_("Defect Type")
    )
    severity = models.CharField(
        max_length=20,
        choices=DefectSeverity.choices,
        verbose_name=_("Severity"),
    )
    status = models.CharField(
        max_length=20,
        choices=DefectStatus.choices,
        default=DefectStatus.OPEN,
        verbose_name=_("Status"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))

    ai_defect_class = models.CharField(
        max_length=200, blank=True, verbose_name=_("AI Defect Class")
    )
    ai_confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.0")),
            MaxValueValidator(Decimal("1.0")),
        ],
        verbose_name=_("AI Confidence"),
    )
    ai_recommendation = models.TextField(
        blank=True, default="", verbose_name=_("AI Recommendation")
    )
    ai_verdict = models.CharField(
        max_length=20,
        choices=DefectVerdict.choices,
        blank=True,
        verbose_name=_("AI Verdict"),
    )

    verdict = models.CharField(
        max_length=20,
        choices=DefectVerdict.choices,
        blank=True,
        verbose_name=_("Verdict"),
    )
    inspector = models.ForeignKey(
        "core.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspected_defects",
        verbose_name=_("Inspector"),
    )
    responsible_employee = models.ForeignKey(
        "core.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsible_defects",
        verbose_name=_("Responsible Employee"),
    )

    repaired_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Repaired At")
    )
    inspected_at = models.DateTimeField(verbose_name=_("Inspected At"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    history = HistoricalRecords()

    objects = DefectQuerySet.as_manager()

    class Meta:
        verbose_name = _("Defect")
        verbose_name_plural = _("Defects")
        ordering = ["-inspected_at"]
        indexes = [
            models.Index(fields=["status", "severity"]),
            models.Index(fields=["status", "node"]),
            models.Index(fields=["department", "status"]),
            models.Index(fields=["inspected_at"]),
        ]

    def __str__(self) -> str:
        node = self.get_node_display()
        defect_type = self.get_defect_type_display()
        wagon_number = self.wagon.number if self.wagon_id else "—"
        return f"{node} — {defect_type} (Wagon: {wagon_number})"

    @property
    def is_repaired(self) -> bool:
        return self.status == DefectStatus.CLOSED

    def set_status(self, status: str) -> None:
        """Save a new status, stamping repaired_at when it closes."""
        self.status = status
        fields = ["status"]

        if status == DefectStatus.CLOSED:
            self.repaired_at = timezone.now()
            fields.append("repaired_at")

        self.save(update_fields=fields)
