from django.utils.translation import gettext_lazy as _

# User data keys
UD_DEFECT = "defect"
UD_RESP_SEARCH = "_resp_search"
UD_LAST_MEDIA_GROUP = "_last_media_group"
UD_EDITING = "_editing"
# [chat_id, message_id] of the defect form's one screen
UD_SCREEN = "_screen"
UD_AI_CHAT_HISTORY = "_ai_chat_history"
UD_AI_CHAT_LAST = "_ai_chat_last"

# All user_data keys touched by the defect conversation, cleared on cancel
DEFECT_USER_DATA_KEYS = (
    UD_DEFECT,
    UD_RESP_SEARCH,
    UD_LAST_MEDIA_GROUP,
    UD_EDITING,
    UD_SCREEN,
)

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
)

BTN_NEW_DEFECT = _("📋 New Defect")
BTN_OPEN_DEFECTS = _("📊 Open Defects")
BTN_ASK = _("🤖 AI Assistant")
BTN_HELP = _("ℹ️ Help")

BTN_SKIP = _("⏭️ Skip")
BTN_SAVE = _("✅ Save")
BTN_CANCEL = _("❌ Cancel")
BTN_DONE = _("✅ Done")
BTN_CLEAR = _("🗑 Clear")
