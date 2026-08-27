"""One-time web sign-in tokens handed out over Telegram.

The bot has already established who someone is — an emailed OTP proved they own
the address on their Employee record — but that proof lives in a chat, not in a
browser session. A token here is the bridge: the bot sends a link containing
one, and following it signs that browser in.

Tokens are random and stored server-side rather than signed and self-contained.
A signed token stays valid for its whole lifetime no matter how often it is
replayed, and these arrive in a Telegram chat that keeps its history forever.
Holding them in Redis means redeeming one deletes it, so a link found in an old
chat is worthless. It also mirrors how apps.bot.services.otp already works.
"""

import secrets

from django.core.cache import cache

# Long enough that guessing is hopeless, short enough to sit in a URL.
_TOKEN_BYTES = 32
_PREFIX = "web_login_token:"

# Deliberately short. The link is meant to be followed straight away, from the
# chat where it just arrived; it is not a password to keep.
TOKEN_TTL = 600  # 10 minutes


def _key(token: str) -> str:
    return f"{_PREFIX}{token}"


def issue(user_id: int) -> str:
    """Create a single-use sign-in token for this user and return it."""
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    cache.set(_key(token), user_id, timeout=TOKEN_TTL)
    return token


def redeem(token: str) -> int | None:
    """Consume a token, returning the user id it was issued for.

    Returns ``None`` when the token is unknown, already used or expired — the
    caller cannot tell these apart, and should not: each means the same thing to
    the person holding the link.
    """
    if not token:
        return None
    key = _key(token)
    user_id = cache.get(key)
    if user_id is None:
        return None
    cache.delete(key)
    return user_id
