from django.utils.translation import gettext_lazy as _


class AuthMessages:
    """Attaching a Telegram account to an existing web account.

    There are no messages for entering an email or a verification code: this
    bot never establishes anybody's identity. That happens on the web, and the
    only thing carried here is a one-time token from an already-signed-in
    session.
    """

    NOT_CONNECTED = _(
        "👋 <b>Welcome!</b>\n\n"
        "This chat is not connected to an account yet.\n\n"
        "Sign in to the web app and press <b>Connect Telegram</b>:\n"
        "{site_url}"
    )

    LINK_OK = _("✅ <b>Telegram connected!</b>")

    LINK_TOKEN_INVALID = _(
        "⚠️ This connection link has expired or has already been used.\n\n"
        "Open <b>Connect Telegram</b> in the web app again to get a new one."
    )

    LINK_NO_EMPLOYEE = _(
        "⚠️ This account is not linked to an active employee record.\n"
        "Please contact your administrator."
    )

    LINK_ALREADY_TAKEN = _(
        "⚠️ This Telegram account is already connected to another employee.\n"
        "Disconnect it there first, or contact your administrator."
    )

    LOGIN_LINK_BUTTON = _("🔐 Open the web app")

    LOGIN_LINK_FAILED = _("⚠️ Could not create a sign-in link. Please try /start again.")
