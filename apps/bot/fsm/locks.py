"""Per-user asyncio locks.

An asyncio.Lock cannot live in FSM state — it is not JSON. It also cannot be
shared across processes, which is fine: the bot polls with handle_as_tasks
disabled, so updates are handled one at a time and nothing here is ever
contended. It becomes load-bearing the moment updates run concurrently, which
is what the webhook cutover will do.

The photo debounce is the one exception today: its flush runs as a real
background task, so it does contend with an arriving photo.
"""

import asyncio

_locks: dict[int, asyncio.Lock] = {}


def user_lock(user_id: int) -> asyncio.Lock:
    """Return this user's lock, creating it on first use.

    Never evicted. Bounded by the number of employees, and a Lock is tiny.
    """
    return _locks.setdefault(user_id, asyncio.Lock())
