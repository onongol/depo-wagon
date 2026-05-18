import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.constants import (
    DefectNode,
    DefectSeverity,
    DefectStatus,
    DefectType,
    DefectVerdict,
)


class Defect(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wagon = models.ForeignKey(
        "core.Wagon",
        on_delete=models.CASCADE,
        related_name="defects",
        verbose_name=_("Wagon"),
    )
    node = models.CharField(
        max_length=20, choices=DefectNode.choices, verbose_name=_("Node")
    )
    defect = models.CharField(
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
    ai_confidence = models.FloatField(
        null=True, blank=True, verbose_name=_("AI Confidence")
    )
    ai_recommendation = models.TextField(
        blank=True, verbose_name=_("AI Recommendation")
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

    repaired_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Repaired At")
    )
    inspected_at = models.DateTimeField(verbose_name=_("Inspected At"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    history = HistoricalRecords()

    @property
    def is_repaired(self) -> bool:
        return self.status == DefectStatus.RESOLVED

    def __str__(self):
        return f"{self.get_node_display()} — {self.get_defect_display()} ({self.wagon})"

    class Meta:
        verbose_name = _("Defect")
        verbose_name_plural = _("Defects")
        ordering = ["-inspected_at"]
        indexes = [
            models.Index(fields=["status", "severity"]),
            models.Index(fields=["node"]),
            models.Index(fields=["inspected_at"]),
        ]
