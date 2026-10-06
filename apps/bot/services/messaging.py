from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup
    from aiogram.utils.formatting import Text


@sync_to_async
def queue_messages(
    employee_ids: list[int],
    text: Text,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Hand each message to the worker, which retries what Telegram defers."""
    from apps.bot.tasks import send_to_employee_task

    kwargs = text.as_kwargs()
    entities = [
        entity.model_dump(mode="json", exclude_none=True)
        for entity in kwargs["entities"]
    ]
    markup = (
        reply_markup.model_dump(mode="json", exclude_none=True)
        if reply_markup
        else None
    )
    for employee_id in employee_ids:
        send_to_employee_task.delay(employee_id, kwargs["text"], entities, markup)
