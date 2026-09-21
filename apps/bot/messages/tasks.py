from django.utils.translation import gettext_lazy as _


class TaskMessages:
    """Notices around the open-defects screens"""

    NO_TASKS = _("✅ You have no open defects.")

    STATUS_CHANGED = _("✅ Status changed: {status}")

    DEFECT_UNAVAILABLE = _("⚠️ This defect is no longer available.")

    STATUS_CHANGE_REFUSED = _("⚠️ This status change is no longer possible.")

    STATUS_CHANGE_FAILED = _("❌ Failed to update status. Please try again.")
