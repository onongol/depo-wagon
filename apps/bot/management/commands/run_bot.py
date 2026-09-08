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
        from apps.bot.fsm import make_storage

        bot = make_bot()
        storage = make_storage()
        dp = make_dispatcher(storage)

        try:
            # Also clears a webhook registration left over from an earlier run;
            # polling and a webhook cannot both be active on one token.
            await bot.delete_webhook(drop_pending_updates=drop_pending)
            await dp.start_polling(
                bot,
                # PTB ran with max_concurrent_updates=1, so the bot has always
                # handled one update at a time. aiogram defaults to a task per
                # update, which would turn every FSM write into a
                # read-modify-write race. Do not flip this without the locking
                # that a concurrent bot needs.
                handle_as_tasks=False,
                allowed_updates=["message", "callback_query"],
            )
        finally:
            await bot.session.close()
            await storage.close()
