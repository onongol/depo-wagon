from django.utils.translation import gettext_lazy as _


class EmailMessages:
    """Email templates used by the mail-sending services."""

    OTP_SUBJECT = _("Wagon Depot — Verification Code")
    OTP_BODY = _(
        "Hello, {first_name}!\n\n"
        "Your Telegram bot verification code:\n\n"
        "    {code}\n\n"
        "The code is valid for 10 minutes.\n"
        "If you did not request this, please ignore this email.\n\n"
        "— Wagon Depot System"
    )

    CREDENTIALS_SUBJECT = _("Wagon Depot — Your Password")
    CREDENTIALS_BODY = _(
        "Hello, {first_name}!\n\n"
        "Your account has been created successfully.\n\n"
        "Email    : {email}\n"
        "Password : {password}\n\n"
        "Please change your password after your first login.\n\n"
        "— Wagon Depot System"
    )
