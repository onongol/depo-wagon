import logging
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.constants import FSMKey
from apps.bot.fsm import clear_defect_keys
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.states import DefectSG
from apps.bot.user_data import is_current_schema
from apps.bot.utils.screens import answer_anew, close_screen

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext
    from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

_START_AGAIN = _("Sorry — please start it again.")


def build_form_outdated_text() -> Text:
    return as_list(
        Text(
            "♻️ ",
            _(
                "The bot was updated while you were filling this in, so the form "
                "could not be carried over."
            ),
        ),
        _START_AGAIN,
        sep="\n\n",
    )


def build_form_lost_text() -> Text:
    return as_list(
        Text("⌛ ", _("This form is no longer available.")),
        _START_AGAIN,
        sep="\n\n",
    )


async def _announce(event: TelegramObject, text: Text) -> None:
    """Ends the form, so it brings the menu back."""
    if isinstance(event, Message):
        await event.answer(**text.as_kwargs(), reply_markup=main_menu_keyboard())
        return

    if not isinstance(event, CallbackQuery):
        return

    with suppress(TelegramBadRequest):
        await event.answer()

    await answer_anew(event, **text.as_kwargs(), reply_markup=main_menu_keyboard())


class DefectFormMiddleware(BaseMiddleware):
    """Inside DefectSG a step always has a form to load, so none checks for None.

    Outer runs ahead of StateFilter, so every feature's updates pass through.
    A form an older build wrote is dropped wherever it is found, silently
    outside DefectSG. Inside it, a dropped or missing form ends the flow here,
    and a scene's absorb never gets to swallow the tap without a word.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext = data["state"]
        stored = (await state.get_data()).get(FSMKey.DEFECT)

        if stored and is_current_schema(stored):
            return await handler(event, data)

        if stored:
            logger.info("Discarding a defect form written by an older state schema")
            await close_screen(event.bot, state)
            await clear_defect_keys(state)

        if data.get("raw_state") not in DefectSG.__all_states_names__:
            return await handler(event, data)

        if not stored:
            logger.warning("A defect step was reached without its form")
        await state.set_state(None)
        await _announce(
            event, build_form_outdated_text() if stored else build_form_lost_text()
        )
        return None
