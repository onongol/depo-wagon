from django.utils.translation import gettext_lazy as _

from apps.defects.constants import DefectStatus

TASKS_PAGE_SIZE = 5

LIST_NUMBER_EMOJI = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")

STATUS_TRANSITIONS = {
    DefectStatus.OPEN: (DefectStatus.IN_PROGRESS, DefectStatus.CLOSED),
    DefectStatus.IN_PROGRESS: (DefectStatus.OPEN, DefectStatus.CLOSED),
    DefectStatus.CLOSED: (),
}

BTN_CHANGE_STATUS = _("⚙️ Change status")
BTN_PREV = _("⬅️ Previous")
BTN_NEXT = _("Next ➡️")
BTN_BACK = _("↩️ Back")
BTN_CONFIRM = _("✅ Confirm")
BTN_OPEN_CARD = _("📄 Open card")
