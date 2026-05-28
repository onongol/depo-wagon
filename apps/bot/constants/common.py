from django.utils.translation import gettext_lazy as _
from telegram.constants import ParseMode

PARSE_MODE = ParseMode.HTML

# User data keys
UD_EMPLOYEE = "employee"
UD_REG = "registration"
UD_DEFECT = "defect"

BTN_NEW_DEFECT = _("📋 New Defect")
BTN_OPEN_DEFECTS = _("📊 Open Defects")
BTN_HELP = _("ℹ️ Help")

BTN_SKIP = _("⏭ Skip")
BTN_SAVE = _("✅ Save")
BTN_CANCEL = _("❌ Cancel")
BTN_ADD = _("➕ Add")
BTN_DONE = _("✅ Done")
