from aiogram.enums import ParseMode

from .ai_chat import AiChatMessages
from .common import CommonMessages


class BotMessages(
    CommonMessages,
    AiChatMessages,
):
    """All Telegram bot strings, composed from per-domain message mixins."""

    PARSE_MODE = ParseMode.HTML
