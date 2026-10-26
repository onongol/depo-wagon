import enum


class LinkStatus(enum.StrEnum):
    """Outcome of attaching a Telegram chat via a web-issued deep-link token."""

    OK = "ok"
    INVALID_TOKEN = "invalid_token"  # noqa: S105
    NO_EMPLOYEE = "no_employee"
    ALREADY_LINKED = "already_linked"
    OFFER_EXPIRED = "offer_expired"
