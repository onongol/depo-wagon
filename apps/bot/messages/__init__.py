from telegram.constants import ParseMode

from .auth import AuthMessages
from .common import CommonMessages
from .defects import DefectMessages
from .email import EmailMessages
from .support import SupportMessages


class BotMessages(CommonMessages, AuthMessages, DefectMessages, SupportMessages):
    """All Telegram bot strings, composed from per-domain message mixins."""

    PARSE_MODE = ParseMode.HTML


__all__ = ["BotMessages", "EmailMessages"]
