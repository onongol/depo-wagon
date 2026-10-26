import asyncio
import logging

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import InlineKeyboardMarkup, MessageEntity
from celery import shared_task

logger = logging.getLogger(__name__)


async def _send(
    chat_id: int, text: str, entities: list[dict], reply_markup: dict | None
) -> None:
    from apps.bot.bot import make_bot

    async with make_bot() as bot:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            entities=[MessageEntity.model_validate(e) for e in entities],
            reply_markup=(
                InlineKeyboardMarkup.model_validate(reply_markup)
                if reply_markup
                else None
            ),
        )


@shared_task(
    bind=True,
    max_retries=5,
    name="bot.send_to_employee",
)
def send_to_employee_task(
    self,
    employee_id: int,
    text: str,
    entities: list[dict],
    # A default, so a task queued before the keyboard existed still runs
    reply_markup: dict | None = None,
) -> None:
    """Telegram's refusals end it; its outages and rate limits retry."""
    from apps.core.models import Employee

    chat_id = (
        Employee.objects.filter(pk=employee_id, is_active=True)
        .values_list("telegram_id", flat=True)
        .first()
    )
    if chat_id is None:
        return

    try:
        asyncio.run(_send(chat_id, text, entities, reply_markup))
    except TelegramRetryAfter as exc:
        raise self.retry(exc=exc, countdown=exc.retry_after) from exc
    except (TelegramNetworkError, TelegramServerError) as exc:
        raise self.retry(exc=exc, countdown=60 * 2**self.request.retries) from exc
    except TelegramAPIError:
        logger.warning(
            "Telegram refused a message to employee %s", employee_id, exc_info=True
        )
