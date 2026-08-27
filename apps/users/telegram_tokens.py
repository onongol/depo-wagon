"""One-time tokens that attach a Telegram account to a signed-in user.

These travel inside a Telegram deep link — ``https://t.me/<bot>?start=<token>``
— which the web app hands to someone who is *already authenticated*. Tapping it
makes Telegram send ``/start <token>`` to the bot, and the bot attaches that
chat to whoever the token was issued for.

Issuing from an authenticated session is the whole point: identity is already
settled by allauth before a token exists, so the bot never has to establish it
again. That is what removed the emailed one-time codes this project used to
have.

Same storage reasoning as apps.users.login_tokens: random and held in Redis
rather than signed and self-contained, so redeeming one destroys it.
"""

import secrets

from django.core.cache import cache

_TOKEN_BYTES = 32
_PREFIX = "tg_link_token:"

# Short: the link is meant to be tapped straight away, from the page that just
# rendered it. A stale one lingering in a browser is not useful to anybody.
TOKEN_TTL = 600  # 10 minutes


def _key(token: str) -> str:
    return f"{_PREFIX}{token}"


def issue(user_id: int) -> str:
    """Create a single-use linking token for this user and return it."""
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    cache.set(_key(token), user_id, timeout=TOKEN_TTL)
    return token


def redeem(token: str) -> int | None:
    """Consume a token, returning the user id it was issued for.

    ``None`` covers unknown, already used and expired alike — the difference is
    not something the person holding the link can act on.
    """
    if not token:
        return None
    key = _key(token)
    user_id = cache.get(key)
    if user_id is None:
        return None
    cache.delete(key)
    return user_id
