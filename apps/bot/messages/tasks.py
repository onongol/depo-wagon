from django.utils.translation import gettext_lazy as _


class TaskMessages:
    """The open-defects list (/my_tasks) and its status changes."""

    TASKS_HEADER = _("📋 <b>Open Defects</b> ({total} total, {start}–{end})\n")

    NO_TASKS = _("✅ You have no open defects.")

    STATUS_CHANGE_REFUSED = _(
        "⚠️ Could not change the status of this defect. The list has been refreshed."
    )

    STATUS_CHANGE_FAILED = _("❌ Failed to update status. Please try again.")
