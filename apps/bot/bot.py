from aiogram import Bot
from django.conf import settings


def make_bot() -> Bot:
    """Build the Bot with no default parse_mode: the AI answer goes out as plain
    text, and HTML parsing would break on a stray < or &."""
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)
