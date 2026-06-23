from telegram.constants import ParseMode

from .ai_chat import AiChatMessages
from .auth import AuthMessages
from .common import CommonMessages
from .defects import DefectMessages
from .email import EmailMessages
from .support import SupportMessages


class BotMessages(
    CommonMessages, AuthMessages, DefectMessages, SupportMessages, AiChatMessages
):
    """All Telegram bot strings, composed from per-domain message mixins."""

    PARSE_MODE = ParseMode.HTML


__all__ = ["BotMessages", "EmailMessages"]
