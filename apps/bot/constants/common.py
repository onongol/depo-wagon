from django.utils.translation import gettext_lazy as _

# Human factor only
EDIT_RESPONSIBLE = "responsible"
# Every type but a human factor
EDIT_MEASUREMENTS = "measurements"

# Fields offered for re-editing from the summary screen: (EditCB.field, button label)
EDIT_FIELDS = (
    ("wagon", _("🚃 Wagon")),
    ("node", _("🔧 Node")),
    ("part_number", _("🔢 Part №")),
    ("defect_type", _("🏷️ Type")),
    (EDIT_RESPONSIBLE, _("👤 Responsible")),
    ("photos", _("📸 Photos")),
    (EDIT_MEASUREMENTS, _("📐 Measurements")),
    ("description", _("📝 Description")),
    ("severity", _("🌡️ Severity")),
    ("verdict", _("👨‍🔧 Verdict")),
)

BTN_NEW_DEFECT = _("📋 New Defect")
BTN_OPEN_DEFECTS = _("📊 Open Defects")
BTN_ASK = _("🤖 AI Assistant")
BTN_HELP = _("ℹ️ Help")

BTN_BACK = _("↩️ Back")
BTN_SKIP = _("⏭️ Skip")
BTN_SAVE = _("✅ Save")
BTN_CANCEL = _("❌ Cancel")
BTN_DONE = _("✅ Done")
BTN_CLEAR = _("🗑 Clear")
