from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10MB


def validate_photo_size(image):
    """Validator to ensure uploaded photo does not exceed size limit."""
    if image.size > MAX_PHOTO_BYTES:
        raise ValidationError(
            _("Photo size %(size)s exceeds the 10 MB limit."),
            params={"size": f"{image.size / 1024 / 1024:.1f} MB"},
        )
