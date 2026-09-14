from django.utils.translation import gettext_lazy as _

from apps.core.constants import EmployeeRole
from apps.defects.constants import DefectSeverity, DefectStatus

TASKS_PAGE_SIZE = 5

# Change the status of only the defects they inspected
ROLES_CHANGING_OWN_STATUS = frozenset({EmployeeRole.INSPECTOR})

SEVERITY_EMOJI = {
    DefectSeverity.LOW: "🟢",
    DefectSeverity.MEDIUM: "🟡",
    DefectSeverity.HIGH: "🟠",
    DefectSeverity.CRITICAL: "🔴",
}

# Shown in the defect list (only active statuses)
STATUS_LABEL = {
    DefectStatus.OPEN: _("🔵 Open"),
    DefectStatus.IN_PROGRESS: _("🟡 In Progress"),
}

# Available options when changing status
STATUS_OPTIONS = [
    (_("🔵 Open"), DefectStatus.OPEN),
    (_("🟡 In Progress"), DefectStatus.IN_PROGRESS),
    (_("🟢 Closed"), DefectStatus.CLOSED),
]

# Navigation button labels
BTN_PREV = _("⬅️ Previous")
BTN_NEXT = _("Next ➡️")
BTN_BACK = _("↩️ Back")
