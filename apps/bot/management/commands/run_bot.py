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
        from apps.bot.application import create_application

        self.stdout.write(
            self.style.SUCCESS("🤖 Telegram bot starting (polling mode)...")
        )
        self.stdout.write("Press Ctrl+C to stop.\n")

        app = create_application()

        try:
            app.run_polling(
                drop_pending_updates=options["drop_pending"],
                allowed_updates=["message", "callback_query"],
            )
        except KeyboardInterrupt:
            pass

        self.stdout.write(self.style.WARNING("Bot stopped."))
