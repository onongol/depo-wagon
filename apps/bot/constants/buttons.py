from django.utils.translation import gettext_lazy as _

# Main menu
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
BTN_CONFIRM = _("✅ Confirm")
BTN_CONNECT = _("✅ Connect")

# Offered when New Defect is pressed while a form is already open
BTN_CONTINUE = _("▶️ Continue")
BTN_START_OVER = _("🔄 Start over")

# Responsible employee picker pagination arrows
BTN_PAGE_PREV = "◀️"
BTN_PAGE_NEXT = "▶️"
# Drops the picker's search
BTN_ALL_EMPLOYEES = _("🔄 All employees")

# Open defects
BTN_PREV = _("⬅️ Previous")
BTN_NEXT = _("Next ➡️")
BTN_OPEN_CARD = _("📄 Open card")
BTN_CHANGE_STATUS = _("⚙️ Change status")

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
