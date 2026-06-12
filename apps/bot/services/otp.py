"""OTP generation and verification, backed by Redis (Django cache)."""

import secrets
import string

from asgiref.sync import sync_to_async
from django.core.cache import cache

from apps.bot.constants import OtpStatus

OTP_TTL = 600  # 10 minutes
OTP_MAX_ATTEMPTS = 3  # max wrong guesses before OTP is invalidated
_OTP_PREFIX = "bot_otp:"


def _otp_key(email: str) -> str:
    """Generate the Redis key for storing OTP data for a given email."""
    return f"{_OTP_PREFIX}{email.lower().strip()}"


@sync_to_async
def generate_and_store_otp(email: str, employee_id: int) -> str:
    """Generate a 6-digit OTP, store in Redis (10 min TTL). Returns the code."""
    code = "".join(secrets.choice(string.digits) for _ in range(6))

    cache.set(
        _otp_key(email),
        {"code": code, "employee_id": employee_id, "attempts": 0},
        timeout=OTP_TTL,
    )
    return code


@sync_to_async
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
