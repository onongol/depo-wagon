"""Message filters with no aiogram built-in."""

from typing import TYPE_CHECKING

from aiogram.enums import MessageEntityType
from aiogram.filters import BaseFilter

if TYPE_CHECKING:
    from aiogram.types import Message


class NotACommand(BaseFilter):
    """The negation of PTB's filters.COMMAND, used by every free-text step.

    Matches PTB exactly: a command is the *first* entity being a bot_command at
    offset 0. A message merely mentioning /something later in the text is
    ordinary text, which matters because a wagon number or a defect description
    may legitimately contain a slash.
    """

    async def __call__(self, message: Message) -> bool:
        entities = message.entities
        if not entities:
            return True

        first = entities[0]
        return not (first.type == MessageEntityType.BOT_COMMAND and first.offset == 0)
