from typing import TYPE_CHECKING

from aiogram.enums import MessageEntityType
from aiogram.filters import BaseFilter

if TYPE_CHECKING:
    from aiogram.types import Message


class NotACommand(BaseFilter):
    """Used by every free-text step so a command doesn't get read as input.

    Checks entities rather than a leading "/", since a wagon number or defect
    description may legitimately contain a slash.
    """

    async def __call__(self, message: Message) -> bool:
        entities = message.entities
        if not entities:
            return True

        first = entities[0]
        return not (first.type == MessageEntityType.BOT_COMMAND and first.offset == 0)
