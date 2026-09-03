"""Emails telling an account owner that their Telegram link changed.

allauth's own mail plumbing is not available for these. ``send_notification_mail``
reads the client IP off the request, and even the adapter's ``send_mail`` resolves
the current site through one; a link is made in the bot process, where there is no
request to read.
"""

import logging

from allauth.account import app_settings as account_settings
from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)

CONNECTED = "connected"
DISCONNECTED = "disconnected"

_TEMPLATES = {
    CONNECTED: "emails/telegram_connected",
    DISCONNECTED: "emails/telegram_disconnected",
}


def send_telegram_link_email(user, action: str) -> bool:
    """Mail the owner about one link change. Returns whether anything was sent."""
    if not account_settings.EMAIL_NOTIFICATIONS:
        return False

    email = EmailAddress.objects.get_primary_email(user)
    if not email:
        logger.warning(
            "No primary email for user %s, skipping %s notice", user.pk, action
        )
        return False

    prefix = _TEMPLATES[action]
    context = {
        "user": user,
        "telegram_url": (
            f"{settings.SITE_URL.rstrip('/')}{reverse('web:telegram_connect')}"
        ),
    }

    subject = render_to_string(f"{prefix}_subject.txt", context)
    subject = " ".join(subject.splitlines()).strip()
    body = render_to_string(f"{prefix}_message.txt", context).strip()

    EmailMultiAlternatives(
        f"{settings.ACCOUNT_EMAIL_SUBJECT_PREFIX}{subject}",
        body,
        settings.DEFAULT_FROM_EMAIL,
        [email],
    ).send()
    return True


def notify_telegram_link_change(user, action: str) -> None:
    """Send the notice. Losing it must not fail the link change itself."""
    try:
        send_telegram_link_email(user, action)
    except Exception:
        logger.exception(
            "Could not send the telegram %s notice for user %s", action, user.pk
        )
