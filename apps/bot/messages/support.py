from django.utils.translation import gettext_lazy as _


class SupportMessages:
    """Support relay: user questions and support replies."""

    SUPPORT_REPLY = _("💬 <b>Reply from support:</b>\n\n{text}")

    SUPPORT_REPLY_HEADER = _("💬 <b>Reply from support:</b>")

    SUPPORT_REPLY_DELIVERED = _("✅ Delivered to the user.")

    SUPPORT_REPLY_FAILED = _("⚠️ Couldn't deliver — the user may have blocked the bot.")
