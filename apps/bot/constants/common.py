from django.utils.translation import gettext_lazy as _
from telegram.constants import ParseMode

PARSE_MODE = ParseMode.HTML

# User data keys
UD_EMPLOYEE = "employee"
UD_REG = "registration"
UD_DEFECT = "defect"
UD_RESP_EMPLOYEES = "_resp_employees"
UD_RESP_SEARCH = "_resp_search"
UD_LAST_PHOTO_MSG = "_last_photo_msg"

# All user_data keys touched by the defect conversation, cleared on cancel
DEFECT_USER_DATA_KEYS = (
    UD_DEFECT,
    UD_RESP_EMPLOYEES,
    UD_RESP_SEARCH,
    UD_LAST_PHOTO_MSG,
)

# JobQueue job-name prefix for debouncing photo media-group (album) batches
PHOTO_MG_JOB_PREFIX = "photo_mg_"

BTN_NEW_DEFECT = _("📋 New Defect")
BTN_OPEN_DEFECTS = _("📊 Open Defects")
BTN_HELP = _("ℹ️ Help")

BTN_SKIP = _("⏭ Skip")
BTN_SAVE = _("✅ Save")
BTN_CANCEL = _("❌ Cancel")
BTN_ADD = _("➕ Add")
BTN_DONE = _("✅ Done")
