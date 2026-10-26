from aiogram import Bot
from django.conf import settings


def make_bot() -> Bot:
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)
