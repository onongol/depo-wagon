from django.db import models
from django.utils.translation import gettext_lazy as _


class DocumentStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    READY = "ready", _("Ready")
    ERROR = "error", _("Error")
