from django.utils.translation import gettext_lazy as _


class SupportMessages:
    """Support relay: user questions and support replies."""

    SUPPORT_ASK = _(
        "✍️ Write your question and I'll forward it to the support team.\n"
        "<i>To exit, type /cancel.</i>"
    )

    SUPPORT_SENT = _(
        "✅ Your question has been sent. The support team will reply here in the bot."
    )

    SUPPORT_UNAVAILABLE = _(
        "⚠️ Support is unavailable right now. Please contact @Erdenebayaraa directly."
    )

    SUPPORT_REQUEST = _(
        "🆘 <b>Support request</b>\n\n"
        "👤 From: {identity}\n"
        "💬 {username}\n\n"
        "<b>Question:</b>\n{question}\n\n"
        "<i>↩️ Reply to this message to answer the user.</i>"
    )

    SUPPORT_REPLY = _("💬 <b>Reply from support:</b>\n\n{text}")

    SUPPORT_REPLY_HEADER = _("💬 <b>Reply from support:</b>")

    SUPPORT_REPLY_DELIVERED = _("✅ Delivered to the user.")

    SUPPORT_REPLY_FAILED = _(
        "⚠️ Couldn't deliver — the user may have blocked the bot."
    )
