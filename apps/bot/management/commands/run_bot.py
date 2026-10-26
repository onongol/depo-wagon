import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import (
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from django.core.management.base import BaseCommand

if TYPE_CHECKING:
    from aiogram import Bot

logger = logging.getLogger(__name__)

WEBHOOK_ATTEMPTS = 5
WEBHOOK_BACKOFF = 1.0


async def _delete_webhook(bot: Bot, *, drop_pending: bool) -> None:
    """Retry transient failures, as polling does; anything else is a real error."""
    for attempt in range(WEBHOOK_ATTEMPTS):
        try:
            await bot.delete_webhook(drop_pending_updates=drop_pending)
        except (TelegramNetworkError, TelegramRetryAfter, TelegramServerError) as exc:
            if attempt == WEBHOOK_ATTEMPTS - 1:
                raise
            delay = (
                exc.retry_after
                if isinstance(exc, TelegramRetryAfter)
                else WEBHOOK_BACKOFF * 2**attempt
            )
            logger.warning("deleteWebhook failed, retrying in %ss: %s", delay, exc)
            await asyncio.sleep(delay)
        else:
            return


async def _run_polling(*, drop_pending: bool) -> None:
    from apps.bot.bot import make_bot
    from apps.bot.dispatcher import make_dispatcher
    from apps.bot.fsm import make_isolation, make_storage

    bot = make_bot()
    storage = make_storage()

    try:
        dp = make_dispatcher(storage, make_isolation(storage))
        await _delete_webhook(bot, drop_pending=drop_pending)
        await dp.start_polling(bot, handle_as_tasks=True)
    finally:
        await bot.session.close()
        await storage.close()


class Command(BaseCommand):
    help = "Run the Telegram bot in polling mode (development)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--drop-pending",
            action="store_true",
            default=False,
            help="Drop all pending updates that arrived while the bot was offline.",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("🤖 Telegram bot starting (polling mode)...")
        )
        self.stdout.write("Press Ctrl+C to stop.\n")

        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(_run_polling(drop_pending=options["drop_pending"]))

        self.stdout.write(self.style.WARNING("Bot stopped."))
