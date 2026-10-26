"""A Bot that records API calls instead of making them.

The unit tests call handlers directly with fake arguments, which cannot say
anything about routing, filters, middlewares or the order updates are offered
to routers. Feeding a real Update through a real Dispatcher can, and a session
that never reaches the network is all it takes.
"""

from typing import TYPE_CHECKING, Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Chat, Message, User

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from aiogram.methods import TelegramMethod

TEST_TOKEN = "42:TESTTOKENTESTTOKENTESTTOKENTESTTOKEN"
BOT_ID = 42


class MockedSession(BaseSession):
    """Answers every call with a plausible result and remembers the request."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod] = []
        self.refusals: dict[str, str] = {}
        self._next_message_id = 1000

    async def make_request(
        self, bot: Bot, method: TelegramMethod, timeout: int | None = None
    ) -> Any:
        self.requests.append(method)
        if refusal := self.refusals.get(method.__api_method__):
            raise TelegramBadRequest(method=method, message=refusal)
        return self._result_for(bot, method)

    def _result_for(self, bot: Bot, method: TelegramMethod) -> Any:
        returning = method.__returning__
        if returning is bool or returning is None:
            return True
        if Message in getattr(returning, "__args__", (returning,)):
            return self._make_message(bot, method)
        return True

    def _make_message(self, bot: Bot, method: TelegramMethod) -> Message:
        self._next_message_id += 1
        chat_id = getattr(method, "chat_id", 1) or 1
        # Bound, or editing it raises a RuntimeError error_handler swallows.
        return Message(
            message_id=self._next_message_id,
            date=0,
            chat=Chat(id=int(chat_id), type="private"),
            from_user=User(id=BOT_ID, is_bot=True, first_name="Bot"),
            text=getattr(method, "text", None) or "",
        ).as_(bot)

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes]:
        yield b""

    async def close(self) -> None:
        return

    # --- assertions ---

    def calls(self, api_method: str) -> list[TelegramMethod]:
        return [m for m in self.requests if m.__api_method__ == api_method]

    def method_names(self) -> list[str]:
        return [m.__api_method__ for m in self.requests]

    def clear(self) -> None:
        self.requests.clear()

    def refuse(self, api_method: str, message: str) -> None:
        """Answer every later call to api_method with a 400 carrying message."""
        self.refusals[api_method] = message


def make_mocked_bot() -> Bot:
    return Bot(token=TEST_TOKEN, session=MockedSession())
