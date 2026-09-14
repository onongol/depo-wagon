import asyncio
import contextlib
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


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
            asyncio.run(self._run(drop_pending=options["drop_pending"]))

        self.stdout.write(self.style.WARNING("Bot stopped."))

    async def _run(self, *, drop_pending: bool) -> None:
        from apps.bot.bot import make_bot
        from apps.bot.dispatcher import make_dispatcher
        from apps.bot.fsm import make_isolation, make_storage

        bot = make_bot()
        storage = make_storage()
        dp = make_dispatcher(storage, make_isolation(storage))

        try:
            # Also clears a webhook registration left over from an earlier run;
            # polling and a webhook cannot both be active on one token.
            await bot.delete_webhook(drop_pending_updates=drop_pending)
            await dp.start_polling(
                bot, handle_as_tasks=True, allowed_updates=["message", "callback_query"]
            )
        finally:
            await bot.session.close()
            await storage.close()
