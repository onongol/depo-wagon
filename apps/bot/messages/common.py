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
