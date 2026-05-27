"""
Telegram webhook view for production use.

Telegram sends POST requests to this endpoint for every update.
The bot application processes them asynchronously via a persistent event loop.

Setup:
  1. Set TELEGRAM_WEBHOOK_URL and TELEGRAM_WEBHOOK_SECRET in .env
  2. Run: python manage.py set_webhook
  3. Deploy with a public HTTPS URL
"""

import asyncio
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# Persistent application instance (created once per process)
_app = None
# Persistent event loop (keeps handler state between requests)
_loop = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


def _get_app():
    global _app
    if _app is None:
        from apps.bot.application import create_application

        _app = create_application()
        _get_loop().run_until_complete(_app.initialize())
        logger.info("Bot application initialised for webhook mode.")
    return _app


@csrf_exempt
def webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed.")

    # Verify secret token sent by Telegram
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    expected = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    if expected and secret != expected:
        logger.warning("Webhook: invalid secret token received.")
        return HttpResponseForbidden("Forbidden.")

    try:
        from telegram import Update

        app = _get_app()
        data = json.loads(request.body)
        update = Update.de_json(data, app.bot)
        _get_loop().run_until_complete(app.process_update(update))

    except Exception as exc:
        logger.error("Webhook processing error: %s", exc, exc_info=True)
        # Return 200 anyway — Telegram retries on non-2xx responses
        return HttpResponse("Error logged.", status=200)

    return HttpResponse("OK")
