"""The aiogram Bot instance."""

from aiogram import Bot
from django.conf import settings


def make_bot() -> Bot:
    """Build the Bot.

    No DefaultBotProperties, and in particular no default parse_mode: several
    messages are sent as plain text on purpose, the AI answer among them. A
    global HTML default would parse arbitrary model output as markup and fail
    on any stray angle bracket or ampersand. The 59 call sites that do want
    HTML pass parse_mode explicitly.
    """
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)
