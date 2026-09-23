from django.utils.translation import gettext_lazy as _


class CommonMessages:
    """Greetings, help, cancel and bot-profile metadata."""

    BOT_DESCRIPTION = _(
        "Register wagon defects step by step: wagon, department, node, type and "
        "severity, with photos and measurements, plus an instant AI assessment.\n\n"
        "Tap the Menu button or send /start to begin."
    )

    BOT_SHORT_DESCRIPTION = _(
        "Register and track wagon defects with photos, measurements and AI analysis."
    )

    SESSION_ERROR = _(
        "⚠️ Something went wrong. Try again, or send /cancel to start over."
    )

    BUTTON_EXPIRED = _(
        "⏳ This button is no longer valid — the bot has restarted since it was "
        "sent.\n\nSend /start to begin again."
    )

    UNHANDLED_MESSAGE = _(
        "⚠️ There is no step waiting for this message.\n\n"
        "An unfinished form expires after a while — tap <b>Menu</b> or send "
        "/help to start again."
    )

    HELP_TEXT = _(
        "🤖 <b>Wagon Defect Registration Bot</b>\n\n"
        "<b>How to register a defect:</b>\n"
        "1️⃣ Tap <b>📋 New Defect</b>\n"
        "2️⃣ Enter 🚃 the wagon number\n"
        "3️⃣ Choose department, node, type and severity\n"
        "4️⃣ Attach 📸 photos\n"
        "5️⃣ Enter measurements\n"
        "6️⃣ Add a 📝 description defect and details\n"
        "7️⃣ Review the summary — tap a field (Wagon, Node…) to ✏️ edit it, then <b>✅ Save</b>\n"
        "8️⃣ Wait for the 🤖 AI analysis, then submit your own verdict\n\n"
        "📊 <b>Open Defects</b> — view and update open defects.\n"
        "❌ <b>Cancel</b> — stop the current step at any time.\n\n"
        "💡 Tap the <b>Menu</b> button next to the message field to see all commands.\n\n"
        "📞 Questions? Send /support and the team will reply to you."
    )
