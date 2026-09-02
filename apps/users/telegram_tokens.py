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
_USER_PREFIX = "tg_link_user:"

# Short: the link is meant to be tapped straight away, from the page that just
# rendered it. A stale one lingering in a browser is not useful to anybody.
TOKEN_TTL = 600  # 10 minutes


def _key(token: str) -> str:
    return f"{_PREFIX}{token}"


def _user_key(user_id: int) -> str:
    return f"{_USER_PREFIX}{user_id}"


def issue(user_id: int) -> str:
    """Create a single-use linking token for this user and return it.

    Issuing revokes whatever token this user held before, so reloading the
    connect page leaves one working link rather than a growing pile of them.
    """
    previous = cache.get(_user_key(user_id))
    if previous:
        cache.delete(_key(previous))

    token = secrets.token_urlsafe(_TOKEN_BYTES)
    cache.set(_key(token), user_id, timeout=TOKEN_TTL)
    cache.set(_user_key(user_id), token, timeout=TOKEN_TTL)
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
    cache.delete(_user_key(user_id))
    return user_id
