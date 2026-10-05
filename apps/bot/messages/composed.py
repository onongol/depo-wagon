from aiogram.enums import ParseMode

from .ai_chat import AiChatMessages
from .common import CommonMessages
from .defects import DefectMessages
from .support import SupportMessages
from .tasks import TaskMessages


class BotMessages(
    CommonMessages,
    DefectMessages,
    TaskMessages,
    SupportMessages,
    AiChatMessages,
):
    """All Telegram bot strings, composed from per-domain message mixins."""

    PARSE_MODE = ParseMode.HTML
