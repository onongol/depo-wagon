import hashlib
import secrets

from django.core.cache import cache

# 43 characters once urlsafe-encoded; Telegram caps a ?start= payload at 64.
_TOKEN_BYTES = 32
_TOKEN_TTL = 600  # 10 minutes
_PREFIX = "tg_link_token:"
_USER_PREFIX = "tg_link_user:"


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _key(digest: str) -> str:
    return f"{_PREFIX}{digest}"


def _user_key(user_id: int) -> str:
    return f"{_USER_PREFIX}{user_id}"


def issue(user_id: int) -> str:
    """Create a single-use linking token for this user and return it.

    Issuing revokes whatever token this user held before, so reloading the
    connect page leaves one working link rather than a growing pile of them.
    Revocation is best-effort: two issues racing each other can leave both
    tokens live until they expire. Both belong to the same user, so the cost is
    a link that outlives its page, not a wider door.
    """
    revoke(user_id)

    token = secrets.token_urlsafe(_TOKEN_BYTES)
    digest = _digest(token)
    cache.set(_key(digest), user_id, timeout=_TOKEN_TTL)
    cache.set(_user_key(user_id), digest, timeout=_TOKEN_TTL)
    return token


def redeem(token: str) -> int | None:
    """Consume a token, returning the user id it was issued for.

    ``None`` covers unknown, already used and expired alike — the difference is
    not something the person holding the link can act on.

    Deletes the tg_link_token:<digest> key.
    If two concurrent requests attempt to redeem the same token simultaneously,
    cache.delete(key) will return True only for the first one.
    """
    if not token:
        return None

    digest = _digest(token)
    key = _key(digest)
    user_id = cache.get(key)
    if user_id is None:
        return None

    if not cache.delete(key):
        return None

    # The page may have issued a newer token meanwhile; its index must survive.
    user_key = _user_key(user_id)
    if cache.get(user_key) == digest:
        cache.delete(user_key)
    return user_id


def revoke(user_id: int) -> None:
    """Kill this user's live token, if any, such as one left on a screen."""
    user_key = _user_key(user_id)
    digest = cache.get(user_key)
    if digest:
        cache.delete_many([_key(digest), user_key])
