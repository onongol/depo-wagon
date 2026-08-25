"""Email sending for the bot (OTP codes and generated credentials)."""

import logging

from asgiref.sync import sync_to_async
from django.core.mail import send_mail

from apps.bot.messages import EmailMessages as M

logger = logging.getLogger(__name__)


def _send_otp_email(email: str, code: str, first_name: str) -> bool:
    """Send the OTP verification code to the employee's email."""
    try:
        send_mail(
            subject=str(M.OTP_SUBJECT),
            message=str(M.OTP_BODY).format(first_name=first_name, code=code),
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("OTP email sent to %s", email)
        return True
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", email, exc)
        return False


def _send_credentials_email(email: str, password: str, first_name: str) -> bool:
    """Send the generated password to the employee's email."""
    try:
        send_mail(
            subject=str(M.CREDENTIALS_SUBJECT),
            message=str(M.CREDENTIALS_BODY).format(
                first_name=first_name, email=email, password=password
            ),
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("Credentials email sent to %s", email)
        return True
    except Exception as exc:
        logger.error("Failed to send credentials email to %s: %s", email, exc)
        return False


# Async wrappers for use inside PTB handlers
send_otp_email = sync_to_async(_send_otp_email)
send_credentials_email = sync_to_async(_send_credentials_email)
