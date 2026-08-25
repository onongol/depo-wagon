from django.utils.translation import gettext_lazy as _


class AuthMessages:
    """Login, email validation and OTP (Telegram side)."""

    WELCOME_NEW = _("👋 <b>Welcome!</b>\n\nEnter your email:")

    EMAIL_INVALID = _(
        "❌ Invalid email address.\n\nPlease try again <i>(e.g. user@example.com)</i>:"
    )

    EMAIL_NOT_FOUND = _(
        "❌ <b>{email}</b> is not registered in the system.\n\n"
        "Enter a valid email or contact your administrator.\n"
        "/cancel — exit"
    )

    EMAIL_ALREADY_LINKED = _(
        "⚠️ This email is already linked to another Telegram account.\n"
        "Please contact your administrator."
    )

    OTP_SENT = _(
        "📧 A verification code has been sent to <b>{email}</b>.\n\n"
        "Check your email and enter the <b>6-digit code</b>:\n"
        "<i>(Code is valid for 10 minutes)</i>"
    )

    OTP_SEND_FAILED = _("⚠️ Failed to send email. Please try again.\n/cancel — exit")

    OTP_EXPIRED = _("⏰ The code has expired.\n\nPlease enter your email again:")

    OTP_MAX_ATTEMPTS = _(
        "🚫 Too many incorrect attempts. Locked.\n\nPlease enter your email again:"
    )

    OTP_WRONG = _("❌ Incorrect code. Please try again:")

    REGISTERED_NEW = _(
        "✅ <b>Registration successful!</b>\n\n"
        "📧 Your password has been sent to <b>{email}</b>.\n"
        "Please check your email."
    )

    TELEGRAM_LINKED = _("✅ <b>Telegram account linked successfully!</b>")
