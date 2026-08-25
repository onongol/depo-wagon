import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Register or remove the Telegram webhook URL"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--delete",
            action="store_true",
            help="Remove the webhook (switch to polling mode).",
        )
        group.add_argument(
            "--info",
            action="store_true",
            help="Show current webhook info from Telegram.",
        )

    def handle(self, *args, **options):
        asyncio.run(self._run(options))

    async def _run(self, options):
        from telegram import Bot

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

        if options["info"]:
            info = await bot.get_webhook_info()
            self.stdout.write(f"URL:             {info.url or '(not set)'}")
            self.stdout.write(f"Pending updates: {info.pending_update_count}")
            self.stdout.write(f"Last error:      {info.last_error_message or '—'}")
            return

        if options["delete"]:
            await bot.delete_webhook(drop_pending_updates=True)
            self.stdout.write(
                self.style.WARNING("✅ Webhook removed. Use run_bot for polling.")
            )
            return

        # Register webhook
        base_url = settings.TELEGRAM_WEBHOOK_URL.rstrip("/")
        webhook_url = f"{base_url}/api/v1/bot/webhook/"
        secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")

        await bot.set_webhook(
            url=webhook_url,
            secret_token=secret or None,
            allowed_updates=["message", "callback_query"],
        )

        self.stdout.write(self.style.SUCCESS(f"✅ Webhook set: {webhook_url}"))
        if secret:
            self.stdout.write("   Secret token: configured ✓")
        else:
            self.stdout.write(
                self.style.WARNING(
                    "   ⚠️  TELEGRAM_WEBHOOK_SECRET not set — "
                    "anyone can send fake updates to your endpoint."
                )
            )
