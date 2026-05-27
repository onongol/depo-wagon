from django.utils.translation import gettext_lazy as _

PAGE_SIZE = 5

SEVERITY_EMOJI = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🟠",
    "critical": "🔴",
}

# Shown in the defect list (only active statuses)
STATUS_LABEL = {
    "open": _("🔵 Open"),
    "in_progress": _("🟡 In Progress"),
}

# Available options when changing status
STATUS_OPTIONS = [
    (_("🔵 Open"), "open"),
    (_("🟡 In Progress"), "in_progress"),
    (_("🟢 Closed"), "closed"),
]

# Navigation button labels
BTN_PREV = _("⬅️ Previous")
BTN_NEXT = _("Next ➡️")
BTN_BACK = _("↩️ Back")
