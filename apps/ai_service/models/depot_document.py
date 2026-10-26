from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.ai_service.constants import DocumentStatus
from apps.core.mixins import UpdatedAtMixin


class DepotDocument(UpdatedAtMixin, models.Model):
    """A document uploaded to the AI service, with its processing status."""

    title = models.CharField(max_length=255, verbose_name=_("Title"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    file = models.FileField(upload_to="depot_documents/", verbose_name=_("File"))
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
        verbose_name=_("Status"),
    )
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Depot Document")
        verbose_name_plural = _("Depot Documents")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
