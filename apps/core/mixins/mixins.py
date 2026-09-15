from django.db import models


class UpdatedAtMixin(models.Model):
    """Add updated_at to update_fields: auto_now skips fields that are not listed."""

    class Meta:
        abstract = True

    def save(self, *args, update_fields=None, **kwargs) -> None:
        if update_fields:
            update_fields = {*update_fields, "updated_at"}
        super().save(*args, update_fields=update_fields, **kwargs)
