import logging

from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from apps.users import telegram_tokens

logger = logging.getLogger(__name__)


@receiver(user_logged_out)
def revoke_telegram_link_token(sender, user, **kwargs) -> None:
    """A link still on screen must not outlive the session that issued it.

    Password changes arrive here too, via ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE.
    """
    if user is None:
        return
    try:
        telegram_tokens.revoke(user.pk)
    except Exception:
        # Runs before the session is flushed: raising would keep them signed in.
        logger.exception("Revoking the Telegram link token of user %s failed", user.pk)
