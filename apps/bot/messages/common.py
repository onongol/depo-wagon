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
