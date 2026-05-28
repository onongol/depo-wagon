import logging
import random
import string

from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.core.mail import send_mail

from apps.bot.constants import OtpStatus

logger = logging.getLogger(__name__)

OTP_TTL = 600  # 10 minutes
OTP_MAX_ATTEMPTS = 3  # max wrong guesses before OTP is invalidated
_OTP_PREFIX = "bot_otp:"


def _otp_key(email: str) -> str:
    """Generate the Redis key for storing OTP data for a given email."""
    return f"{_OTP_PREFIX}{email.lower().strip()}"


def generate_and_store_otp(email: str, employee_id: int) -> str:
    """Generate a 6-digit OTP, store in Redis (10 min TTL). Returns the code."""
    code = "".join(random.choices(string.digits, k=6))

    cache.set(
        _otp_key(email),
        {"code": code, "employee_id": employee_id, "attempts": 0},
        timeout=OTP_TTL,
    )
    return code


def verify_otp(email: str, entered_code: str):
    """
    Check the entered code against the stored OTP.

    Returns:
        (employee_id, "ok")     — correct code
        (None, "wrong")         — wrong code (attempts counter incremented)
        (None, "expired")       — OTP not found or expired
        (None, "max_attempts")  — too many wrong attempts, OTP deleted
    """
    key = _otp_key(email)
    data = cache.get(key)

    if not data:
        return None, OtpStatus.EXPIRED

    if data["code"] != entered_code.strip():
        data["attempts"] += 1
        if data["attempts"] >= OTP_MAX_ATTEMPTS:
            cache.delete(key)
            return None, OtpStatus.MAX_ATTEMPTS
        cache.set(key, data, timeout=OTP_TTL)
        return None, OtpStatus.WRONG

    cache.delete(key)
    return data["employee_id"], OtpStatus.OK


def _send_otp_email(email: str, code: str, first_name: str) -> bool:
    """Send the OTP verification code to the employee's email."""
    try:
        send_mail(
            subject="Вагон Депо — Нэвтрэх код / Verification Code",
            message=(
                f"Сайн байна уу, {first_name}!\n\n"
                f"Таны Telegram бот нэвтрэх код:\n\n"
                f"    {code}\n\n"
                f"Код 10 минут хүчинтэй.\n"
                f"Хэрэв та энэ хүсэлт гаргаагүй бол энэ и-мэйлийг үл тоомсорлоно уу.\n\n"
                f"— Вагон Депо систем"
            ),
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
            subject="Вагон Депо — Таны нууц үг / Your Password",
            message=(
                f"Сайн байна уу, {first_name}!\n\n"
                f"Таны бүртгэл амжилттай үүслээ.\n\n"
                f"И-мэйл   : {email}\n"
                f"Нууц үг  : {password}\n\n"
                f"Анхны нэвтрэлтийн дараа нууц үгээ заавал солино уу.\n\n"
                f"— Вагон Депо систем"
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
