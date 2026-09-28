from django.utils.translation import gettext_lazy as _

from apps.defects.constants import DefectSeverity, DefectVerdict

# AI result display: value → (emoji, plain_text)
VERDICT_TEXT = {
    DefectVerdict.OK: ("✅", _("OK")),
    DefectVerdict.REPAIR_SOON: ("🟡", _("Repair Soon")),
    DefectVerdict.REPAIR_NOW: ("🟠", _("Repair Now")),
    DefectVerdict.DECOMMISSION: ("🔴", _("Decommission")),
}

VERDICT_EMOJI = {v: e for v, (e, _) in VERDICT_TEXT.items()}

# Employee keyboard buttons: (value, label)
VERDICT_CHOICES = [
    (DefectVerdict.OK, _("✅ OK")),
    (DefectVerdict.REPAIR_SOON, _("🟡 Repair Soon")),
    (DefectVerdict.REPAIR_NOW, _("🟠 Repair Now")),
    (DefectVerdict.DECOMMISSION, _("🔴 Decommission")),
]

VERDICT_LABELS = dict(VERDICT_CHOICES)

# Severity choices: (label, value) for user display and selection
SEVERITY_CHOICES = [
    (_("🟢 Low"), DefectSeverity.LOW),
    (_("🟡 Medium"), DefectSeverity.MEDIUM),
    (_("🟠 High"), DefectSeverity.HIGH),
    (_("🔴 Critical"), DefectSeverity.CRITICAL),
]

SEVERITY_LABELS = {value: str(label) for label, value in SEVERITY_CHOICES}

# Responsible employee picker pagination arrows
BTN_PAGE_PREV = "◀️"
BTN_PAGE_NEXT = "▶️"

# Drops the picker's search
BTN_ALL_EMPLOYEES = _("🔄 All employees")

# Offered when New Defect is pressed while a form is already open
BTN_CONTINUE = _("▶️ Continue")
BTN_START_OVER = _("🔄 Start over")
