from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.defects.validators import validate_photo_size


class DefectPhoto(models.Model):
    """Model representing a photo associated with a defect."""

    defect = models.ForeignKey(
        "defects.Defect",
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("Defect"),
    )
    image = models.ImageField(
        upload_to="defects/%Y/%m/",
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"]),
            validate_photo_size,
        ],
        verbose_name=_("Photo"),
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Uploaded At"),
    )

    class Meta:
        verbose_name = _("Defect Photo")
        verbose_name_plural = _("Defect Photos")
        ordering = ["-uploaded_at"]
        indexes = [models.Index(fields=["-uploaded_at"])]

    def __str__(self) -> str:
        return f"Photo #{self.defect_id} ({self.uploaded_at:%Y-%m-%d})"
