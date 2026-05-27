"""Shared bot constants."""

from django.utils.translation import gettext_lazy as _
from telegram.constants import ParseMode

PARSE_MODE = ParseMode.HTML

BTN_NEW_DEFECT = _("📋 New Defect")
BTN_OPEN_DEFECTS = _("📊 Open Defects")
BTN_HELP = _("ℹ️ Help")


BTN_SKIP = _("⏭ Skip")
BTN_SAVE = _("✅ Save")
BTN_CANCEL = _("❌ Cancel")
BTN_ADD = _("➕ Add")
BTN_DONE = _("✅ Done")

# ── Verdict ───────────────────────────────────────────────────────────────────
# AI result display: value → (emoji, plain_text)
VERDICT_TEXT = {
    "ok":           ("✅", _("OK")),
    "repair_soon":  ("🟡", _("Repair Soon")),
    "repair_now":   ("🟠", _("Repair Now")),
    "decommission": ("🔴", _("Decommission")),
}

VERDICT_EMOJI = {v: e for v, (e, _) in VERDICT_TEXT.items()}

# Employee keyboard buttons + done message: (value, label)
VERDICT_CHOICES = [
    ("ok",           _("✅ OK")),
    ("repair_soon",  _("🟡 Repair Soon")),
    ("repair_now",   _("🟠 Repair Now")),
    ("decommission", _("🔴 Decommission")),
]

VERDICT_LABELS = {v: label for v, label in VERDICT_CHOICES}

# ── Severity ──────────────────────────────────────────────────────────────────
SEVERITY_CHOICES = [
    (_("🟢 Low"), "low"),
    (_("🟡 Medium"), "medium"),
    (_("🟠 High"), "high"),
    (_("🔴 Critical"), "critical"),
]

SEVERITY_LABELS = {value: str(label) for label, value in SEVERITY_CHOICES}
