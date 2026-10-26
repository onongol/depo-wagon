import logging

from allauth.account import app_settings as account_settings
from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from apps.core.mail import serialize_message
from apps.core.tasks import send_queued_email

logger = logging.getLogger(__name__)

CONNECTED = "connected"
DISCONNECTED = "disconnected"

_TEMPLATES = {
    CONNECTED: "emails/telegram_connected",
    DISCONNECTED: "emails/telegram_disconnected",
}


def build_telegram_link_email(user, action: str) -> EmailMultiAlternatives | None:
    """The notice for one link change, or None when the owner has no address."""
    email = EmailAddress.objects.get_primary_email(user)
    if not email:
        logger.warning(
            "No primary email for user %s, skipping %s notice", user.pk, action
        )
        return None

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

    return EmailMultiAlternatives(
        f"{settings.ACCOUNT_EMAIL_SUBJECT_PREFIX}{subject}",
        body,
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )


def notify_telegram_link_change(user, action: str) -> None:
    """Queue the notice best-effort: one publish attempt, never fails the link change."""
    if not account_settings.EMAIL_NOTIFICATIONS:
        return

    try:
        message = build_telegram_link_email(user, action)
        if message is not None:
            send_queued_email.apply_async((serialize_message(message),), retry=False)
    except Exception:
        logger.exception(
            "Could not queue the telegram %s notice for user %s", action, user.pk
        )
