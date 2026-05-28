import enum


class OtpStatus(str, enum.Enum):
    OK = "ok"
    WRONG = "wrong"
    EXPIRED = "expired"
    MAX_ATTEMPTS = "max_attempts"


class RegStatus(str, enum.Enum):
    CREATED = "created"
    LINKED = "linked"
