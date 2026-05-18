from django.db import models
from django.utils.translation import gettext_lazy as _


class DefectPhoto(models.Model):
    defect = models.ForeignKey(
        "defects.Defect",
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("Defect"),
    )
    image = models.ImageField(upload_to="defects/%Y/%m/", verbose_name=_("Photo"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded At"))

    def __str__(self):
        return f"Photo {self.defect} ({self.uploaded_at:%Y-%m-%d})"

    class Meta:
        verbose_name = _("Photo")
        verbose_name_plural = _("Photos")
        ordering = ["-uploaded_at"]
        indexes = [models.Index(fields=["defect"])]
